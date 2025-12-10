import React, { useMemo } from 'react';
import { View, StyleSheet, Dimensions, Text } from 'react-native';
import { MapContainer, TileLayer, Polyline, useMap, Tooltip, Marker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Removed problematic PNG imports that cause bundling errors with Metro/Webpack
// If markers are broken, we can fix them later with base64 or CDN URLs.

interface ActivityMapProps {
    data?: any[]; // Full activity details with lat, long, altitude, timestamp, speed
    coordinates?: Array<{ lat: number; long: number }>; // Fallback
    width?: number;
    height?: number;
}

const ChangeView = ({ bounds }: { bounds: L.LatLngBoundsExpression }) => {
    const map = useMap();
    if (bounds) {
        map.fitBounds(bounds, { padding: [20, 20] });
    }
    return null;
};

// Color scale helper (Blue -> Green -> Yellow -> Red)
const getElevationColor = (elevation: number, minElev: number, maxElev: number) => {
    if (maxElev === minElev) return '#00FF99';
    const ratio = (elevation - minElev) / (maxElev - minElev);

    // Simple HSL interpolation: 240 (Blue) -> 0 (Red)
    // Blue(240) -> Teal(180) -> Green(120) -> Yellow(60) -> Red(0)
    // Let's map 0->1 ratio to 240->0 hue
    const hue = (1 - ratio) * 240;
    return `hsl(${hue}, 100%, 50%)`;
};

const ActivityMap: React.FC<ActivityMapProps> = ({ data, coordinates, width, height }) => {
    const screenWidth = Dimensions.get('window').width;
    const mapWidth = width || screenWidth - 40;
    const mapHeight = height || 250;

    const { segments, validPoints } = useMemo(() => {
        let points: any[] = data || [];

        // Fallback to coordinates if data not provided
        if ((!points || points.length === 0) && coordinates) {
            points = coordinates.map(c => ({ position_lat: c.lat, position_long: c.long, altitude: 0, timestamp: null, speed: 0 }));
        }

        const valid = points.filter((p: any) => p.position_lat && p.position_long && p.position_lat !== 0 && p.position_long !== 0);

        if (valid.length < 2) return { segments: [], validPoints: [] };

        // Calculate Min/Max Elevation
        const elevations = valid.map((p: any) => p.altitude || 0);
        const minElev = Math.min(...elevations);
        const maxElev = Math.max(...elevations);

        const result: { positions: [number, number][]; color: string; tooltip: string }[] = [];
        const startTime = valid[0].timestamp ? new Date(valid[0].timestamp).getTime() : 0;

        // Helper to shift point perpendicular to bearing
        // Bearing: 0 = North, 90 = East
        const toRad = Math.PI / 180;
        const toDeg = 180 / Math.PI;

        const getShiftedPoint = (lat1: number, lon1: number, lat2: number, lon2: number) => {
            // Calculate bearing
            const dLon = (lon2 - lon1) * toRad;
            const y = Math.sin(dLon) * Math.cos(lat2 * toRad);
            const x = Math.cos(lat1 * toRad) * Math.sin(lat2 * toRad) - Math.sin(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.cos(dLon);
            let brng = Math.atan2(y, x) * toDeg;

            // Shift 90 degrees (Right)
            // Approx 0.00003 degrees ~ 3-4 meters
            const offset = 0.00003;
            const rightOver = (brng + 90) * toRad;

            const latShift = Math.cos(rightOver) * offset;
            const lonShift = Math.sin(rightOver) * offset; // Simplified, technically needs cos(lat) adjustment but fine for small local shifts

            return {
                p1: [lat1 + latShift, lon1 + lonShift] as [number, number],
                p2: [lat2 + latShift, lon2 + lonShift] as [number, number]
            };
        };

        for (let i = 0; i < valid.length - 1; i++) {
            const p1 = valid[i];
            const p2 = valid[i + 1];

            // Apply Offset
            const shifted = getShiftedPoint(p1.position_lat, p1.position_long, p2.position_lat, p2.position_long);

            // Average elevation for segment color
            const avgElev = ((p1.altitude || 0) + (p2.altitude || 0)) / 2;
            const color = getElevationColor(avgElev, minElev, maxElev);

            // Calculate tooltip info
            let tooltipText = "";
            if (p1.timestamp && startTime > 0) {
                const t = new Date(p1.timestamp).getTime();
                const mins = Math.floor((t - startTime) / 60000);
                const speed = p1.speed || 0;
                const pace = speed > 0 ? (1000 / speed / 60) : 0;
                const paceMin = Math.floor(pace);
                const paceSec = Math.round((pace - paceMin) * 60);

                tooltipText = `${mins}m - ${paceMin}:${paceSec < 10 ? '0' : ''}${paceSec}/km`;
            }

            result.push({
                positions: [shifted.p1, shifted.p2],
                color,
                tooltip: tooltipText
            });
        }
        return { segments: result, validPoints: valid };
    }, [data, coordinates]);

    if (!validPoints || validPoints.length < 2) {
        return (
            <View style={[styles.container, { width: mapWidth, height: mapHeight, justifyContent: 'center', alignItems: 'center' }]}>
                <div style={{ color: '#fff' }}>No GPS Data Available</div>
            </View>
        );
    }

    // Optimization: If too many segments, Leaflet can lag.
    // However, ~1000-2000 lines should be fine on desktop web.
    // We only render simplified polylines.

    // Bounds for fitting view
    const bounds = L.latLngBounds(validPoints.map(p => [p.position_lat, p.position_long]));

    return (
        <View style={{ width: mapWidth, height: mapHeight, borderRadius: 12, overflow: 'hidden' }}>
            <MapContainer
                center={[validPoints[0].position_lat, validPoints[0].position_long]}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
                scrollWheelZoom={true}
                dragging={true}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                />

                {/* Render colored segments */}
                {segments.map((seg, index) => (
                    <Polyline
                        key={index}
                        positions={seg.positions}
                        pathOptions={{ color: seg.color, weight: 5, opacity: 1 }}
                    >
                        {/* Only add tooltip to every 10th segment to reduce clutter/DOM load, but allow fine-grained hover */}
                        <Tooltip sticky direction="top" opacity={0.9}>
                            {seg.tooltip}
                        </Tooltip>
                    </Polyline>
                ))}

                {/* Start Marker (Green) */}
                {validPoints.length > 0 && (
                    <Marker
                        position={[validPoints[0].position_lat, validPoints[0].position_long]}
                        icon={L.divIcon({
                            className: 'custom-icon',
                            html: `<div style="background-color: #00FF99; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>`,
                            iconSize: [12, 12],
                            iconAnchor: [6, 6]
                        })}
                    >
                        <Tooltip direction="top" offset={[0, -10]} opacity={1}>Start</Tooltip>
                    </Marker>
                )}

                {/* End Marker (Red/Checkered) */}
                {validPoints.length > 1 && (
                    <Marker
                        position={[validPoints[validPoints.length - 1].position_lat, validPoints[validPoints.length - 1].position_long]}
                        icon={L.divIcon({
                            className: 'custom-icon',
                            html: `<div style="background-color: #FF3333; width: 14px; height: 14px; border-radius: 2px; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>`,
                            iconSize: [14, 14],
                            iconAnchor: [7, 7]
                        })}
                    >
                        <Tooltip direction="top" offset={[0, -10]} opacity={1}>Finish</Tooltip>
                    </Marker>
                )}

                <ChangeView bounds={bounds} />
            </MapContainer>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        backgroundColor: '#111',
        borderRadius: 12,
        overflow: 'hidden',
    },
});

export default ActivityMap;
