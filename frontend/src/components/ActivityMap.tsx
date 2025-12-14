import React, { useEffect, useMemo, useRef } from 'react';
import { View, Text, Dimensions, StyleSheet, Platform } from 'react-native';
import MapView, { Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import Svg, { Path, Rect } from 'react-native-svg';

interface ActivityMapProps {
    data?: any[];
    coordinates?: Array<{ latitude: number; longitude: number }>;
    width?: number;
    height?: number;
}

const ActivityMap: React.FC<ActivityMapProps> = ({ data, coordinates, width, height }) => {
    const screenWidth = Dimensions.get('window').width;
    const mapWidth = width || screenWidth - 40;
    const mapHeight = height || 250;
    const mapRef = useRef<MapView>(null);

    const validCoords = useMemo(() => {
        console.log('[MAP] Received coordinates:', coordinates?.length, 'data:', data?.length);

        // Use coordinates directly if provided
        if (coordinates && coordinates.length > 1) {
            console.log('[MAP] Using coordinates prop, first:', coordinates[0]);
            const valid = coordinates.filter((c: any) =>
                c.latitude !== undefined && c.latitude !== null && !isNaN(c.latitude) &&
                c.longitude !== undefined && c.longitude !== null && !isNaN(c.longitude)
            );
            console.log('[MAP] Valid coords:', valid.length);
            return valid;
        }

        // Fallback to data prop
        if (data && data.length > 0) {
            console.log('[MAP] Using data prop');
            const valid = data.filter((d: any) => d.latitude && d.longitude);
            console.log('[MAP] Valid from data:', valid.length);
            return valid;
        }

        console.log('[MAP] No valid data source');
        return [];
    }, [data, coordinates]);

    // For web: render SVG path
    if (Platform.OS === 'web' && validCoords.length > 1) {
        const lats = validCoords.map(c => c.latitude);
        const lons = validCoords.map(c => c.longitude);
        const minLat = Math.min(...lats);
        const maxLat = Math.max(...lats);
        const minLon = Math.min(...lons);
        const maxLon = Math.max(...lons);

        const padding = 20;
        const svgWidth = mapWidth - padding * 2;
        const svgHeight = mapHeight - padding * 2;

        const pathData = validCoords.map((coord, i) => {
            const x = padding + ((coord.longitude - minLon) / (maxLon - minLon)) * svgWidth;
            const y = padding + ((maxLat - coord.latitude) / (maxLat - minLat)) * svgHeight;
            return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
        }).join(' ');

        console.log('[MAP] Rendering SVG with', validCoords.length, 'points');

        return (
            <View style={[styles.container, { width: mapWidth, height: mapHeight }]}>
                <Svg width={mapWidth} height={mapHeight} style={{ backgroundColor: '#0a0a0a' }}>
                    <Rect x={0} y={0} width={mapWidth} height={mapHeight} fill="#0a0a0a" />
                    <Path
                        d={pathData}
                        stroke="#CCFF00"
                        strokeWidth={3}
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                </Svg>
            </View>
        );
    }

    // For native: use MapView
    useEffect(() => {
        if (mapRef.current && validCoords.length > 1) {
            mapRef.current.fitToCoordinates(validCoords, {
                edgePadding: { top: 20, right: 20, bottom: 20, left: 20 },
                animated: true,
            });
        }
    }, [validCoords]);

    if (validCoords.length < 2) {
        console.log('[MAP] Not enough coords, showing no data message');
        return (
            <View style={[styles.container, styles.noDataContainer, { width: mapWidth, height: mapHeight }]}>
                <Text style={styles.noDataText}>No GPS Data Available</Text>
            </View>
        );
    }

    console.log('[MAP] Rendering MapView with', validCoords.length, 'points');

    return (
        <View style={[styles.container, { width: mapWidth, height: mapHeight }]}>
            <MapView
                ref={mapRef}
                style={styles.map}
                provider={PROVIDER_GOOGLE}
                mapType="standard"
                showsUserLocation={false}
                showsMyLocationButton={false}
                scrollEnabled={true}
                zoomEnabled={true}
                pitchEnabled={false}
                rotateEnabled={false}
            >
                <Polyline
                    coordinates={validCoords}
                    strokeColor="#CCFF00"
                    strokeWidth={4}
                    lineCap="round"
                    lineJoin="round"
                />
            </MapView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        overflow: 'hidden',
        borderRadius: 8,
    },
    map: {
        width: '100%',
        height: '100%',
    },
    noDataContainer: {
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#0a0a0a',
    },
    noDataText: {
        color: '#666',
        fontSize: 14,
    },
});

export default ActivityMap;
