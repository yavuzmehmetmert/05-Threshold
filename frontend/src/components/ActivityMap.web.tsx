import React, { useMemo } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import { MapContainer, TileLayer, Polyline, useMap, Tooltip, Marker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for Leaflet marker icons in React (Webpack/Metro issues)
// Using a simple divIcon avoids the need for image assets that might fail to load
const createMarkerIcon = (color: string, size: number) => {
    return L.divIcon({
        className: 'custom-icon',
        html: `<div style="background-color: ${color}; width: ${size}px; height: ${size}px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2]
    });
};

interface ActivityMapProps {
    data?: any[];
    coordinates?: Array<{ latitude: number; longitude: number }>;
    width?: number;
    height?: number;
}

const ChangeView = ({ bounds }: { bounds: L.LatLngBoundsExpression }) => {
    const map = useMap();
    if (bounds && Object.keys(bounds).length > 0) {
        try {
            map.fitBounds(bounds, { padding: [20, 20] });
        } catch (e) {
            console.warn("Map fitBounds failed", e);
        }
    }
    return null;
};

const getElevationColor = (elevation: number, minElev: number, maxElev: number) => {
    if (maxElev === minElev) return '#00FF99';
    const ratio = (elevation - minElev) / (maxElev - minElev);
    const hue = (1 - ratio) * 240;
    return `hsl(${hue}, 100%, 50%)`;
};

const ActivityMap: React.FC<ActivityMapProps> = ({ data, coordinates, width, height }) => {
    const screenWidth = Dimensions.get('window').width;
    const mapWidth = width || screenWidth - 40;
    const mapHeight = height || 250;

    const { segments, validPoints, center } = useMemo(() => {
        let points: any[] = [];
        let source = '';

        // STRATEGY: Prioritize "coordinates" prop because it is explicitly normalized for the map.
        if (coordinates && coordinates.length > 1) {
            source = 'coordinates';
            points = coordinates.map(c => ({
                lat: c.latitude,
                lng: c.longitude,
                alt: (c as any).altitude || 0,
                timestamp: (c as any).timestamp,
                speed: (c as any).speed || 0
            }));
        }
        // Fallback to "data" (Stream)
        else if (data && data.length > 0) {
            source = 'data';
            points = data.map(d => ({
                lat: d.latitude || d.position_lat,
                lng: d.longitude || d.position_long,
                alt: d.altitude || d.enhanced_altitude || 0,
                timestamp: d.timestamp,
                speed: d.speed
            }));
        }

        // Filter invalid points
        const valid = points.filter(p =>
            p.lat !== undefined && p.lat !== null && !isNaN(p.lat) && p.lat !== 0 &&
            p.lng !== undefined && p.lng !== null && !isNaN(p.lng) && p.lng !== 0
        );

        console.log(`[ActivityMap.web] Source: ${source}, Input: ${data?.length}/${coordinates?.length}, Valid: ${valid.length}`);

        if (valid.length < 2) return { segments: [], validPoints: [], center: [0, 0] as [number, number] };

        // Process Segments for Color/Gradient
        const minElev = Math.min(...valid.map(p => p.alt));
        const maxElev = Math.max(...valid.map(p => p.alt));
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

            // Shift 90 degrees (Right side of the road)
            // Offset: 0.0001 degrees is approx 11-12 meters (significantly more separation)
            const offset = 0.00010;
            const rightOver = (brng + 90) * toRad;

            const latShift = Math.cos(rightOver) * offset;
            const lonShift = Math.sin(rightOver) * offset;

            return {
                p1: [lat1 + latShift, lon1 + lonShift] as [number, number],
                p2: [lat2 + latShift, lon2 + lonShift] as [number, number]
            };
        };

        const result: { positions: [number, number][]; color: string; tooltip: string }[] = [];

        for (let i = 0; i < valid.length - 1; i++) {
            const p1 = valid[i];
            const p2 = valid[i + 1];

            // Apply Offset to Separate Lines
            const shifted = getShiftedPoint(p1.lat, p1.lng, p2.lat, p2.lng);

            // Simple coloring
            const avgElev = (p1.alt + p2.alt) / 2;
            const color = getElevationColor(avgElev, minElev, maxElev);

            // Calculate tooltip info
            let tooltipText = `Elev: ${Math.round(p1.alt)}m`;
            if (p1.timestamp && startTime > 0) {
                const t = new Date(p1.timestamp).getTime();
                const mins = Math.floor((t - startTime) / 60000);
                const seconds = Math.floor(((t - startTime) % 60000) / 1000);

                // Calculate Pace (min/km)
                // Speed is usually m/s
                let paceStr = "-";
                if (p1.speed > 0) {
                    const paceMinKm = (1000 / p1.speed) / 60; // min per km
                    const pM = Math.floor(paceMinKm);
                    const pS = Math.round((paceMinKm - pM) * 60);
                    paceStr = `${pM}:${pS < 10 ? '0' : ''}${pS}/km`;
                }

                tooltipText = `${mins}:${seconds < 10 ? '0' : ''}${seconds} | ${paceStr} | ${Math.round(p1.alt)}m`;
            }

            result.push({
                positions: [shifted.p1, shifted.p2],
                color,
                tooltip: tooltipText
            });
        }

        const centerLat = valid[0].lat;
        const centerLng = valid[0].lng;

        return { segments: result, validPoints: valid, center: [centerLat, centerLng] as [number, number] };
    }, [data, coordinates]);

    if (!validPoints || validPoints.length < 2) {
        return (
            <View style={[styles.container, { width: mapWidth, height: mapHeight, justifyContent: 'center', alignItems: 'center' }]}>
                <div style={{ color: '#666', fontFamily: 'System' }}>No GPS Data Available</div>
            </View>
        );
    }

    const bounds = L.latLngBounds(validPoints.map(p => [p.lat, p.lng]));

    return (
        <View style={{ width: mapWidth, height: mapHeight, borderRadius: 12, overflow: 'hidden', backgroundColor: '#111' }}>
            <MapContainer
                center={center}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
                scrollWheelZoom={false}
                dragging={true}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; CARTO'
                />

                {/* Draw Segments */}
                {segments.map((seg, index) => (
                    <Polyline
                        key={index}
                        positions={seg.positions}
                        pathOptions={{ color: seg.color, weight: 4, opacity: 1 }}
                    >
                        <Tooltip sticky direction="top" opacity={0.9}>
                            {seg.tooltip}
                        </Tooltip>
                    </Polyline>
                ))}

                {/* Start/End Markers */}
                <Marker position={[validPoints[0].lat, validPoints[0].lng]} icon={createMarkerIcon('#00FF99', 12)}>
                    <Tooltip>Start</Tooltip>
                </Marker>

                <Marker position={[validPoints[validPoints.length - 1].lat, validPoints[validPoints.length - 1].lng]} icon={createMarkerIcon('#FF3333', 14)}>
                    <Tooltip>Finish</Tooltip>
                </Marker>

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
