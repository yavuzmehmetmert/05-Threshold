import React, { useMemo, useRef, useEffect } from 'react';
import { View, StyleSheet, Dimensions, Text } from 'react-native';
import MapView, { Polyline, PROVIDER_DEFAULT, Marker } from 'react-native-maps';

interface ActivityMapProps {
    data?: any[];
    coordinates: Array<{ lat: number; long: number }>;
    width?: number;
    height?: number;
}

// Color scale helper (Blue -> Green -> Yellow -> Red)
const getElevationColor = (elevation: number, minElev: number, maxElev: number) => {
    if (maxElev === minElev) return '#00FF99';
    const ratio = (elevation - minElev) / (maxElev - minElev);

    // RGB Interpolation for Native (HSL not supported in hex/color names usually, but rgba/rgb is)
    // Let's implement a simple Cold (Blue) -> Hot (Red)
    // 0.0 -> 0, 0, 255 (Blue)
    // 0.5 -> 0, 255, 0 (Green)
    // 1.0 -> 255, 0, 0 (Red)

    let r, g, b;
    if (ratio < 0.5) {
        // Blue to Green
        const localRatio = ratio * 2;
        r = 0;
        g = Math.floor(255 * localRatio);
        b = Math.floor(255 * (1 - localRatio));
    } else {
        // Green to Red
        const localRatio = (ratio - 0.5) * 2;
        r = Math.floor(255 * localRatio);
        g = Math.floor(255 * (1 - localRatio));
        b = 0;
    }

    return `rgb(${r},${g},${b})`;
};

const ActivityMap: React.FC<ActivityMapProps> = ({ data, coordinates, width, height }) => {
    const screenWidth = Dimensions.get('window').width;
    const mapWidth = width || screenWidth - 40;
    const mapHeight = height || 250;
    const mapRef = useRef<MapView>(null);

    const { validCoords, strokeColors } = useMemo(() => {
        let points: any[] = data || [];

        if ((!points || points.length === 0) && coordinates) {
            points = coordinates.map(c => ({ position_lat: c.lat, position_long: c.long, altitude: 0 }));
        }

        const valid = points.filter((p: any) => p.position_lat && p.position_long && p.position_lat !== 0 && p.position_long !== 0);

        if (valid.length < 2) return { validCoords: [], strokeColors: [] };

        const elevations = valid.map((p: any) => p.altitude || 0);
        const minElev = Math.min(...elevations);
        const maxElev = Math.max(...elevations);

        const colors = valid.map((p: any) => getElevationColor(p.altitude || 0, minElev, maxElev));
        const coords = valid.map((p: any) => ({ latitude: p.position_lat, longitude: p.position_long }));

        return { validCoords: coords, strokeColors: colors };
    }, [data, coordinates]);

    useEffect(() => {
        if (mapRef.current && validCoords.length > 1) {
            mapRef.current.fitToCoordinates(validCoords, {
                edgePadding: { top: 20, right: 20, bottom: 20, left: 20 },
                animated: true,
            });
        }
    }, [validCoords]);

    if (validCoords.length < 2) {
        return (
            <View style={[styles.container, { width: mapWidth, height: mapHeight, justifyContent: 'center', alignItems: 'center' }]}>
                <Text style={{ color: '#666' }}>No GPS Data Available</Text>
            </View>
        );
    }

    return (
        <View style={{ width: mapWidth, height: mapHeight, borderRadius: 12, overflow: 'hidden' }}>
            <MapView
                ref={mapRef}
                style={{ width: '100%', height: '100%' }}
                provider={PROVIDER_DEFAULT}
                mapType="mutedStandard"
                userInterfaceStyle="dark"
            >
                <Polyline
                    coordinates={validCoords}
                    strokeWidth={4}
                    strokeColors={strokeColors} // Gradient colors
                    strokeColor="#00FF99" // Fallback
                />

                {/* Start Marker */}
                {validCoords.length > 0 && (
                    <Marker
                        coordinate={validCoords[0]}
                        title="Start"
                        pinColor="green"
                    />
                )}

                {/* End Marker */}
                {validCoords.length > 1 && (
                    <Marker
                        coordinate={validCoords[validCoords.length - 1]}
                        title="Finish"
                        pinColor="red"
                    />
                )}
            </MapView>
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
