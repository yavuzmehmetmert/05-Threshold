import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Dimensions } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ChevronLeft, Clock, MapPin, Heart, Flame, Zap, Wind, Activity, Mountain, Footprints, Timer, ArrowUp } from 'lucide-react-native';
import { VictoryChart, VictoryLine, VictoryAxis, VictoryTheme, VictoryArea, VictoryScatter, VictoryBar, VictoryVoronoiContainer, VictoryTooltip, VictoryLabel, VictoryCursorContainer } from 'victory-native';
import { Defs, LinearGradient, Stop } from 'react-native-svg';
import { useDashboardStore } from '../store/useDashboardStore';
import { ErrorBoundary } from '../components/ErrorBoundary';
import ActivityMap from '../components/ActivityMap';

const { width } = Dimensions.get('window');

const MetricItem = ({ icon: Icon, label, value, unit, color }: any) => (
    <View style={styles.metricItem}>
        <View style={[styles.iconBox, { backgroundColor: color + '20' }]}>
            <Icon color={color} size={20} />
        </View>
        <View>
            <Text style={styles.metricLabel}>{label}</Text>
            <Text style={styles.metricValue}>{value} <Text style={styles.metricUnit}>{unit}</Text></Text>
        </View>
    </View>
);

const ActivityDetailScreen = () => {
    const navigation = useNavigation();
    const route = useRoute<any>();
    const { activity } = route.params;
    const [details, setDetails] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchActivityDetails();
    }, []);

    const fetchActivityDetails = async () => {
        try {
            const response = await fetch(`http://localhost:8000/ingestion/activity/${activity.activityId}`);
            if (response.ok) {
                const data = await response.json();
                setDetails(data);
            }
        } catch (error) {
            console.error('Failed to fetch details:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatDuration = (seconds: number) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h > 0 ? h + 'h ' : ''}${m}m ${s}s`;
    };

    // Prepare data for charts
    const hrData = details.filter(d => d.heart_rate).map((d, i) => ({ x: i, y: d.heart_rate }));
    const paceData = details.filter(d => d.speed).map((d, i) => ({ x: i, y: d.speed * 3.6 })); // m/s to km/h
    const elevationData = details.filter(d => d.altitude).map((d, i) => ({ x: i, y: d.altitude }));

    // GPS Route Data (Lat/Long)
    // Normalize to fit in a square box for visualization
    const routeData = details.filter(d => d.position_lat && d.position_long).map(d => ({ x: d.position_long, y: d.position_lat }));

    // Calculate Averages for Running Dynamics
    const calcAvg = (key: string) => {
        const valid = details.filter(d => d[key]);
        if (valid.length === 0) return 0;
        return valid.reduce((acc, curr) => acc + curr[key], 0) / valid.length;
    };

    const avgVertOsc = calcAvg('vertical_oscillation');
    const avgStrideLen = calcAvg('step_length') / 1000; // mm to m
    const avgGCT = calcAvg('stance_time');
    const avgVertRatio = calcAvg('vertical_ratio');

    // Efficiency Factor: Speed (m/min) / HR. Speed is m/s. m/min = m/s * 60.
    const avgSpeedVal = calcAvg('speed');
    const avgHRVal = calcAvg('heart_rate');
    const efficiencyFactor = avgHRVal > 0 ? (avgSpeedVal * 60) / avgHRVal : 0;

    // Cardiac Drift (Pa:HR/pw:HR Decoupling)
    // Formula: ((EF_first_half - EF_second_half) / EF_first_half) * 100
    // EF = Speed / HR (or Power / HR)
    const calculateDecoupling = () => {
        if (details.length < 120) return 0; // Need at least 2 mins of data

        const midPoint = Math.floor(details.length / 2);
        const firstHalf = details.slice(0, midPoint).filter(d => d.speed > 0.1 && d.heart_rate > 0);
        const secondHalf = details.slice(midPoint).filter(d => d.speed > 0.1 && d.heart_rate > 0);

        if (firstHalf.length === 0 || secondHalf.length === 0) return 0;

        const calcEF = (arr: any[]) => {
            const avgSpeed = arr.reduce((acc, curr) => acc + curr.speed, 0) / arr.length; // m/s
            const avgHR = arr.reduce((acc, curr) => acc + curr.heart_rate, 0) / arr.length;
            return avgHR > 0 ? (avgSpeed * 60) / avgHR : 0;
        };

        const ef1 = calcEF(firstHalf);
        const ef2 = calcEF(secondHalf);

        if (ef1 === 0) return 0;

        // Decoupling is typically positive if efficiency drops (HR goes up for same speed)
        // Values < 5% are good. > 5% indicates lack of aerobic endurance.
        return ((ef1 - ef2) / ef1) * 100;
    };

    const cardiacDrift = calculateDecoupling();

    // Heart Rate Zones
    const { userProfile } = useDashboardStore();
    const maxHr = userProfile.maxHr || 190;
    const hrZones = userProfile.hrZones || [100, 120, 140, 160, 180]; // Fallback if not synced

    const calculateZones = () => {
        const zones = [0, 0, 0, 0, 0]; // Z1, Z2, Z3, Z4, Z5
        details.forEach(d => {
            if (!d.heart_rate) return;
            // Use real floors
            if (d.heart_rate < hrZones[1]) zones[0]++;      // < Z2 Floor (aka Z1)
            else if (d.heart_rate < hrZones[2]) zones[1]++; // < Z3 Floor
            else if (d.heart_rate < hrZones[3]) zones[2]++; // < Z4 Floor
            else if (d.heart_rate < hrZones[4]) zones[3]++; // < Z5 Floor
            else zones[4]++;                                // >= Z5 Floor
        });

        // Convert to minutes and percentage
        const totalDuration = zones.reduce((a, b) => a + b, 0);
        return zones.map((seconds, i) => ({
            label: `Z${i + 1}`,
            seconds: seconds,
            minutes: Math.round(seconds / 60),
            pct: totalDuration > 0 ? (seconds / totalDuration) * 100 : 0,
            color: ['#999999', '#3399FF', '#33FF33', '#FFCC00', '#FF3333'][i]
        }));
    };

    const zoneStats = calculateZones();

    return (
        <ErrorBoundary>
            <ScrollView contentContainerStyle={styles.container}>
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                        <ChevronLeft color="white" size={24} />
                    </TouchableOpacity>
                    <Text style={styles.headerTitle} numberOfLines={1}>{activity.activityName}</Text>
                    <View style={{ width: 24 }} />
                </View>

                {/* Activity Map (Interactive) */}
                <View style={[styles.section, { marginBottom: 20 }]}>
                    <View style={[styles.chartCard, { padding: 0, overflow: 'hidden', height: 350, backgroundColor: '#000', borderWidth: 1, borderColor: '#333' }]}>
                        {loading ? (
                            <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                                <ActivityIndicator color="#CCFF00" />
                            </View>
                        ) : (
                            <ActivityMap
                                data={details}
                                coordinates={details.map(d => ({ lat: d.position_lat, long: d.position_long }))}
                                width={width - 40}
                                height={350}
                            />
                        )}
                        <View style={{ position: 'absolute', bottom: 10, right: 10, padding: 4, backgroundColor: 'rgba(0,0,0,0.7)', borderRadius: 4 }}>
                            <Text style={{ color: '#fff', fontSize: 10 }}>Interactive Map</Text>
                        </View>
                    </View>
                </View>

                {/* Summary Card moved below map */}
                <View style={styles.summaryCard}>
                    <Text style={styles.date}>
                        {new Date(activity.startTimeLocal).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </Text>
                    <Text style={styles.time}>
                        {new Date(activity.startTimeLocal).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                    </Text>

                    <View style={styles.mainStats}>
                        <View style={styles.stat}>
                            <Text style={styles.statValue}>{(activity.distance / 1000).toFixed(2)}</Text>
                            <Text style={styles.statLabel}>Kilometers</Text>
                        </View>
                        <View style={styles.statDivider} />
                        <View style={styles.stat}>
                            <Text style={styles.statValue}>{formatDuration(activity.duration)}</Text>
                            <Text style={styles.statLabel}>Duration</Text>
                        </View>
                    </View>
                </View >

                {/* Removed Old Route Visualization */}

                {/* Detailed Metrics Grid */}
                < View style={styles.section} >
                    <Text style={styles.sectionTitle}>Performance Metrics</Text>
                    <View style={styles.grid}>
                        <MetricItem
                            icon={Wind}
                            label="Avg Speed"
                            value={(activity.avgSpeed * 3.6).toFixed(1)}
                            unit="km/h"
                            color="#00CCFF"
                        />
                        <MetricItem
                            icon={Heart}
                            label="Avg HR"
                            value={activity.averageHeartRate || '-'}
                            unit="bpm"
                            color="#FF3333"
                        />
                        <MetricItem
                            icon={Flame}
                            label="Calories"
                            value={activity.calories || '-'}
                            unit="kcal"
                            color="#FF9900"
                        />
                        <MetricItem
                            icon={Mountain}
                            label="Elevation Gain"
                            value={activity.elevationGain || 0}
                            unit="m"
                            color="#CC00FF"
                        />
                        <MetricItem
                            icon={Footprints}
                            label="Cadence"
                            value={details.length > 0 ? Math.round(details.reduce((acc, curr) => acc + (curr.cadence || 0), 0) / details.length * 2) : '-'}
                            unit="spm"
                            color="#00FF99"
                        />
                        <MetricItem
                            icon={Zap}
                            label="Power"
                            value={details.length > 0 && details[0].power ? Math.round(details.reduce((acc, curr) => acc + (curr.power || 0), 0) / details.length) : '-'}
                            unit="W"
                            color="#FFFF00"
                        />
                        <MetricItem
                            icon={Activity}
                            label="Eff. Factor"
                            value={efficiencyFactor.toFixed(2)}
                            unit=""
                            color="#EEEEEE"
                        />
                    </View>

                    {/* Cardiac Drift Visual Gauge */}
                    <View style={{ marginTop: 20, backgroundColor: '#111', padding: 16, borderRadius: 12 }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                            <Text style={{ color: '#888', fontSize: 12 }}>CARDIAC DRIFT (Decoupling)</Text>
                            <Text style={{ color: cardiacDrift < 5 ? '#00FF00' : '#FF0000', fontWeight: 'bold' }}>{cardiacDrift.toFixed(1)}%</Text>
                        </View>
                        <View style={{ height: 10, backgroundColor: '#333', borderRadius: 5, overflow: 'hidden' }}>
                            {/* Threshold Marker at 5% */}
                            <View style={{ position: 'absolute', left: '33%', width: 2, height: '100%', backgroundColor: '#666', zIndex: 1 }} />

                            <View style={{
                                width: `${Math.min(Math.max(cardiacDrift * 6.6, 0), 100)}%`, // Scale 0-15% to 0-100% width. (15% is usually max reasonable drift)
                                height: '100%',
                                backgroundColor: cardiacDrift < 5 ? '#00FF00' : cardiacDrift < 10 ? '#FFFF00' : '#FF0000'
                            }} />
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 }}>
                            <Text style={{ color: '#444', fontSize: 10 }}>0%</Text>
                            <Text style={{ color: '#444', fontSize: 10 }}>5% (Threshold)</Text>
                            <Text style={{ color: '#444', fontSize: 10 }}>15%+</Text>
                        </View>
                    </View>
                </View >

                {/* Running Dynamics Section */}
                {
                    avgVertOsc > 0 && (
                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>Running Dynamics</Text>
                            <View style={styles.grid}>
                                <MetricItem
                                    icon={ArrowUp}
                                    label="Vert. Osc."
                                    value={avgVertOsc.toFixed(1)}
                                    unit="mm"
                                    color="#FF00FF"
                                />
                                <MetricItem
                                    icon={Footprints}
                                    label="Stride Len"
                                    value={avgStrideLen.toFixed(2)}
                                    unit="m"
                                    color="#00FFFF"
                                />
                                <MetricItem
                                    icon={Timer}
                                    label="GCT"
                                    value={Math.round(avgGCT)}
                                    unit="ms"
                                    color="#FFAA00"
                                />
                                <MetricItem
                                    icon={Activity}
                                    label="Vert. Ratio"
                                    value={avgVertRatio.toFixed(1)}
                                    unit="%"
                                    color="#AAAAAA"
                                />
                            </View>
                        </View>
                    )
                }

                {/* Heart Rate Zones Section */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Heart Rate Zones</Text>
                    <View style={styles.chartCard}>
                        {/* Horizontal Stacked Bar */}
                        <View style={{ width: '100%', height: 30, flexDirection: 'row', borderRadius: 15, overflow: 'hidden' }}>
                            {zoneStats.map((zone, i) => (
                                <View
                                    key={i}
                                    style={{
                                        width: `${zone.pct}%`,
                                        height: '100%',
                                        backgroundColor: zone.color
                                    }}
                                />
                            ))}
                        </View>

                        {/* Legend Below */}
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 12, flexWrap: 'wrap' }}>
                            {zoneStats.map((zone, i) => (
                                <View key={i} style={{ alignItems: 'center', width: '20%' }}>
                                    <Text style={{ color: zone.color, fontWeight: 'bold', fontSize: 12 }}>Z{i + 1}</Text>
                                    <Text style={{ color: '#DDD', fontSize: 12, fontWeight: '600' }}>{Math.round(zone.pct)}%</Text>
                                    <Text style={{ color: '#666', fontSize: 10 }}>{zone.minutes}m</Text>
                                </View>
                            ))}
                        </View>
                    </View>
                </View>

                {/* Charts Section */}
                {
                    !loading && (
                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>Analysis</Text>

                            {/* Heart Rate Chart */}
                            {/* Heart Rate Chart */}
                            <View style={styles.chartCard}>
                                {(() => {
                                    if (hrData.length === 0) return <Text style={{ color: '#666', textAlign: 'center', marginTop: 20 }}>No Heart Rate Data</Text>;

                                    // Calculate Domain and Stops for Gradient
                                    const hrValues = hrData.map(d => d.y);
                                    // Avoid Math.min/max on empty array
                                    const minData = hrValues.length > 0 ? Math.min(...hrValues) : 0;
                                    const maxData = hrValues.length > 0 ? Math.max(...hrValues) : 200;

                                    // Add padding to domain
                                    const minY = Math.floor(minData * 0.95);
                                    const maxY = Math.ceil(maxData * 1.05);
                                    const range = maxY - minY || 1; // Avoid divide by zero

                                    // Helper to get offset % for a HR value (0 at bottom, 1 at top in SVG usually, but let's check coord system)
                                    const getOffset = (val: number) => {
                                        const ratio = (val - minY) / range;
                                        const invRatio = 1 - ratio;
                                        return Math.max(0, Math.min(1, invRatio)); // Clamp
                                    };

                                    // Calculate Minute Grids and Averages
                                    const minuteBuckets: { [key: number]: number[] } = {};
                                    hrData.forEach(d => {
                                        const min = Math.floor(d.x / 60);
                                        if (!minuteBuckets[min]) minuteBuckets[min] = [];
                                        minuteBuckets[min].push(d.y);
                                    });

                                    const avgLabels = Object.keys(minuteBuckets).map(min => {
                                        const vals = minuteBuckets[parseInt(min)];
                                        const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
                                        return { x: parseInt(min) * 60 + 30, y: maxY - 5, label: `${avg}` };
                                    });

                                    // Calculate KM Splits (Vertical Lines)
                                    const kmMarkers: any[] = [];
                                    let nextKm = 1000;

                                    if (details && details.length > 0) {
                                        // Safely parse start time
                                        const startStr = details[0].timestamp;
                                        const startTime = startStr ? new Date(startStr).getTime() : 0;

                                        if (startTime > 0) {
                                            details.forEach(d => {
                                                if (d.distance && d.distance >= nextKm) {
                                                    const tStr = d.timestamp;
                                                    if (tStr) {
                                                        const t = new Date(tStr).getTime();
                                                        const seconds = (t - startTime) / 1000;
                                                        kmMarkers.push({ x: seconds });
                                                        nextKm += 1000;
                                                    }
                                                }
                                            });
                                        }
                                    }

                                    return (
                                        <>
                                            <Text style={[styles.chartTitle, { color: '#FF3333' }]}>Heart Rate</Text>
                                            <VictoryChart
                                                width={width - 40}
                                                height={220}
                                                theme={VictoryTheme.material}
                                                domain={{ y: [minY, maxY] }} // Explicit domain for alignment
                                                containerComponent={
                                                    <VictoryCursorContainer
                                                        cursorDimension="x"
                                                        cursorLabel={({ datum }) => {
                                                            if (!datum || !datum.x) return "";
                                                            const mins = Math.floor(datum.x / 60);
                                                            const secs = Math.floor(datum.x % 60);
                                                            return `${Math.round(datum.y)} bpm\n@ ${mins}:${secs < 10 ? '0' : ''}${secs}`;
                                                        }}
                                                        cursorLabelComponent={
                                                            <VictoryLabel
                                                                style={{ fill: "white", fontSize: 12, fontWeight: "bold" }}
                                                                backgroundStyle={{ fill: "#333", opacity: 0.9, rx: 4 }}
                                                                backgroundPadding={8}
                                                            />
                                                        }
                                                        cursorComponent={
                                                            <VictoryLine style={{ data: { stroke: "#CCFF00", strokeWidth: 1, strokeDasharray: "4, 4" } }} />
                                                        }
                                                    />
                                                }
                                            >
                                                <Defs>
                                                    {/* Gradient Definition */}
                                                    {(() => {
                                                        const safeZones = (hrZones && hrZones.length >= 5) ? hrZones : [100, 120, 140, 160, 180];
                                                        const safeOffset = (val: number | undefined) => {
                                                            if (val === undefined || isNaN(val)) return "0%";
                                                            const ratio = (val - minY) / (range || 1);
                                                            const invRatio = 1 - ratio;
                                                            const clamped = Math.max(0, Math.min(1, invRatio));
                                                            return isNaN(clamped) ? "0%" : `${clamped}`;
                                                        };

                                                        return (
                                                            <LinearGradient id="hrZoneGradient" x1="0" y1="0" x2="0" y2="1">
                                                                <Stop offset="0%" stopColor="#FF3333" />
                                                                <Stop offset={safeOffset(safeZones[4])} stopColor="#FF3333" />
                                                                <Stop offset={safeOffset(safeZones[4])} stopColor="#FFCC00" />
                                                                <Stop offset={safeOffset(safeZones[3])} stopColor="#FFCC00" />
                                                                <Stop offset={safeOffset(safeZones[3])} stopColor="#33FF33" />
                                                                <Stop offset={safeOffset(safeZones[2])} stopColor="#33FF33" />
                                                                <Stop offset={safeOffset(safeZones[2])} stopColor="#3399FF" />
                                                                <Stop offset={safeOffset(safeZones[1])} stopColor="#3399FF" />
                                                                <Stop offset={safeOffset(safeZones[1])} stopColor="#999999" />
                                                                <Stop offset="100%" stopColor="#999999" />
                                                            </LinearGradient>
                                                        );
                                                    })()}
                                                </Defs>

                                                {/* Minute Grids (Vertical) - Darker, Subtle */}
                                                <VictoryAxis
                                                    style={{
                                                        axis: { stroke: "#333" },
                                                        tickLabels: { fill: "#666", fontSize: 10 },
                                                        grid: { stroke: "#222", strokeWidth: 1 }
                                                    }}
                                                    tickValues={Object.keys(minuteBuckets).map(m => parseInt(m) * 60)}
                                                    tickFormat={(t) => {
                                                        const mins = Math.floor(t / 60);
                                                        return `${mins}m`;
                                                    }}
                                                />

                                                {/* KM Markers (Thick Dashed Lines) - NEON HIGHLIGHT */}
                                                {kmMarkers.map((marker, i) => (
                                                    <VictoryLine
                                                        key={`km-${i}`}
                                                        data={[{ x: marker.x, y: minY }, { x: marker.x, y: maxY }]}
                                                        style={{ data: { stroke: "#CCFF00", strokeWidth: 2, strokeDasharray: "8, 4", opacity: 0.8 } }}
                                                    />
                                                ))}

                                                {/* REMOVED STATIC LABELS (VictoryScatter) TO REDUCE CLUTTER */}
                                                {/* Interaction is now handled by VictoryCursorContainer */}

                                                {/* Main Heart Rate Line - Gradient */}
                                                <VictoryLine
                                                    data={hrData}
                                                    interpolation="catmullRom"
                                                    style={{
                                                        data: {
                                                            stroke: "url(#hrZoneGradient)",
                                                            strokeWidth: 3
                                                        }
                                                    }}
                                                />

                                                <VictoryArea
                                                    data={hrData}
                                                    interpolation="catmullRom"
                                                    style={{
                                                        data: { fill: "url(#hrZoneGradient)", fillOpacity: 0.1, stroke: "none" }
                                                    }}
                                                />


                                                <VictoryAxis
                                                    dependentAxis
                                                    style={{
                                                        axis: { stroke: "transparent" },
                                                        tickLabels: { fill: "#666", fontSize: 10 },
                                                        grid: { stroke: "#222", strokeDasharray: "2, 4" }
                                                    }}
                                                />
                                            </VictoryChart>
                                        </>
                                    );
                                })()}
                            </View>


                            {/* Running Dynamics Grid (New) */}
                            {details.some(d => d.power) && (
                                <View style={styles.chartCard}>
                                    <Text style={styles.chartTitle}>Running Dynamics</Text>
                                    <View style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginTop: 10 }}>

                                        {/* Power */}
                                        <View style={styles.dynamicsItem}>
                                            <Text style={styles.dynamicsLabel}>AVG POWER</Text>
                                            <Text style={[styles.dynamicsValue, { color: '#FFCC00' }]}>{Math.round(calcAvg('power'))} <Text style={{ fontSize: 14 }}>W</Text></Text>
                                        </View>

                                        {/* Cadence */}
                                        <View style={styles.dynamicsItem}>
                                            <Text style={styles.dynamicsLabel}>CADENCE</Text>
                                            <Text style={[styles.dynamicsValue, { color: '#00FF99' }]}>{Math.round(calcAvg('cadence'))} <Text style={{ fontSize: 14 }}>spm</Text></Text>
                                        </View>

                                        {/* GCT */}
                                        <View style={styles.dynamicsItem}>
                                            <Text style={styles.dynamicsLabel}>GCT</Text>
                                            <Text style={[styles.dynamicsValue, { color: '#CC00FF' }]}>{Math.round(avgGCT)} <Text style={{ fontSize: 14 }}>ms</Text></Text>
                                        </View>

                                        {/* Vertical Osc */}
                                        <View style={styles.dynamicsItem}>
                                            <Text style={styles.dynamicsLabel}>VERT OSC</Text>
                                            <Text style={[styles.dynamicsValue, { color: '#00CCFF' }]}>{avgVertOsc.toFixed(1)} <Text style={{ fontSize: 14 }}>cm</Text></Text>
                                        </View>
                                    </View>
                                </View>
                            )}

                            {/* Power Chart (New) */}
                            {details.some(d => d.power) && (
                                <View style={styles.chartCard}>
                                    <Text style={[styles.chartTitle, { color: '#FFCC00' }]}>Power (Watts)</Text>
                                    <VictoryChart
                                        width={width - 50}
                                        height={200}
                                        theme={VictoryTheme.material}
                                        containerComponent={
                                            <VictoryCursorContainer
                                                cursorDimension="x"
                                                cursorLabel={({ datum }) => {
                                                    if (!datum || !datum.x) return "";
                                                    const mins = Math.floor(datum.x / 60);
                                                    return `${Math.round(datum.y)} W\n@ ${mins}m`;
                                                }}
                                                cursorLabelComponent={
                                                    <VictoryLabel
                                                        style={{ fill: "white", fontSize: 12, fontWeight: "bold" }}
                                                        backgroundStyle={{ fill: "#333", opacity: 0.9, rx: 4 }}
                                                        backgroundPadding={8}
                                                    />
                                                }
                                                cursorComponent={
                                                    <VictoryLine style={{ data: { stroke: "#FFCC00", strokeWidth: 1, strokeDasharray: "4, 4" } }} />
                                                }
                                            />
                                        }
                                    >
                                        <Defs>
                                            <LinearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1">
                                                <Stop offset="0%" stopColor="#FFCC00" stopOpacity={0.8} />
                                                <Stop offset="100%" stopColor="#FF6600" stopOpacity={0.2} />
                                            </LinearGradient>
                                        </Defs>
                                        <VictoryArea
                                            data={details.map((d, i) => ({ x: i, y: d.power || 0 }))}
                                            style={{
                                                data: { fill: "url(#powerGradient)", stroke: "#FFCC00", strokeWidth: 2 }
                                            }}
                                        />
                                        <VictoryAxis style={{ axis: { stroke: "#333" }, tickLabels: { fill: "#666", fontSize: 10 } }} />
                                        <VictoryAxis dependentAxis style={{ axis: { stroke: "transparent" }, tickLabels: { fill: "#666", fontSize: 10 }, grid: { stroke: "#222", strokeDasharray: "4, 4" } }} />
                                    </VictoryChart>
                                </View>
                            )}

                            {/* Cadence Chart (New) */}
                            {details.some(d => d.cadence) && (
                                <View style={styles.chartCard}>
                                    <Text style={[styles.chartTitle, { color: '#00FF99' }]}>Cadence (spm)</Text>
                                    <VictoryChart
                                        width={width - 50}
                                        height={200}
                                        theme={VictoryTheme.material}
                                        containerComponent={
                                            <VictoryCursorContainer
                                                cursorDimension="x"
                                                cursorLabel={({ datum }) => {
                                                    if (!datum || !datum.x) return "";
                                                    const mins = Math.floor(datum.x / 60);
                                                    return `${Math.round(datum.y)} spm\n@ ${mins}m`;
                                                }}
                                                cursorLabelComponent={
                                                    <VictoryLabel
                                                        style={{ fill: "white", fontSize: 12, fontWeight: "bold" }}
                                                        backgroundStyle={{ fill: "#333", opacity: 0.9, rx: 4 }}
                                                        backgroundPadding={8}
                                                    />
                                                }
                                                cursorComponent={
                                                    <VictoryLine style={{ data: { stroke: "#00FF99", strokeWidth: 1, strokeDasharray: "4, 4" } }} />
                                                }
                                            />
                                        }
                                    >
                                        <Defs>
                                            <LinearGradient id="cadenceGradient" x1="0" y1="0" x2="0" y2="1">
                                                <Stop offset="0%" stopColor="#00FF99" stopOpacity={0.8} />
                                                <Stop offset="100%" stopColor="#009966" stopOpacity={0.2} />
                                            </LinearGradient>
                                        </Defs>
                                        <VictoryLine
                                            data={details.map((d, i) => ({ x: i, y: d.cadence || 0 }))}
                                            style={{
                                                data: { stroke: "#00FF99", strokeWidth: 2 }
                                            }}
                                        />
                                        <VictoryArea
                                            data={details.map((d, i) => ({ x: i, y: d.cadence || 0 }))}
                                            style={{
                                                data: { fill: "url(#cadenceGradient)", fillOpacity: 0.3, stroke: "none" }
                                            }}
                                        />
                                        <VictoryAxis style={{ axis: { stroke: "#333" }, tickLabels: { fill: "#666", fontSize: 10 } }} />
                                        <VictoryAxis dependentAxis domain={[0, 220]} style={{ axis: { stroke: "transparent" }, tickLabels: { fill: "#666", fontSize: 10 }, grid: { stroke: "#222", strokeDasharray: "4, 4" } }} />
                                    </VictoryChart>
                                </View>
                            )}

                            {/* Pace Chart */}
                            <View style={styles.chartCard}>
                                <Text style={[styles.chartTitle, { color: '#00CCFF' }]}>Pace (km/h)</Text>
                                <VictoryChart
                                    width={width - 40}
                                    height={220}
                                    theme={VictoryTheme.material}
                                    containerComponent={
                                        <VictoryCursorContainer
                                            cursorDimension="x"
                                            cursorLabel={({ datum }) => {
                                                if (!datum || !datum.x) return "";
                                                const mins = Math.floor(datum.x / 60);
                                                const secs = Math.floor(datum.x % 60);
                                                return `${datum.y.toFixed(1)} km/h\n@ ${mins}:${secs < 10 ? '0' : ''}${secs}`;
                                            }}
                                            cursorLabelComponent={
                                                <VictoryLabel
                                                    style={{ fill: "white", fontSize: 12, fontWeight: "bold" }}
                                                    backgroundStyle={{ fill: "#333", opacity: 0.9, rx: 4 }}
                                                    backgroundPadding={8}
                                                />
                                            }
                                            cursorComponent={
                                                <VictoryLine style={{ data: { stroke: "#00CCFF", strokeWidth: 1, strokeDasharray: "4, 4" } }} />
                                            }
                                        />
                                    }
                                >
                                    <Defs>
                                        <LinearGradient id="paceGradient" x1="0" y1="0" x2="0" y2="1">
                                            <Stop offset="0%" stopColor="#00CCFF" stopOpacity={0.8} />
                                            <Stop offset="100%" stopColor="#0066FF" stopOpacity={0.2} />
                                        </LinearGradient>
                                    </Defs>
                                    <VictoryArea
                                        data={paceData}
                                        interpolation="catmullRom"
                                        style={{
                                            data: { fill: "url(#paceGradient)", stroke: "#00CCFF", strokeWidth: 2 }
                                        }}
                                    />
                                    <VictoryAxis
                                        style={{
                                            axis: { stroke: "#333" },
                                            tickLabels: { fill: "#666", fontSize: 10 },
                                            grid: { stroke: "#222", strokeWidth: 1 }
                                        }}
                                        tickFormat={(t) => {
                                            const mins = Math.floor(t / 60);
                                            return `${mins}m`;
                                        }}
                                    />
                                    <VictoryAxis
                                        dependentAxis
                                        style={{
                                            axis: { stroke: "transparent" },
                                            tickLabels: { fill: "#666", fontSize: 10 },
                                            grid: { stroke: "#222", strokeDasharray: "4, 4" }
                                        }}
                                    />
                                </VictoryChart>
                            </View>

                            {/* Elevation Chart */}
                            <View style={styles.chartCard}>
                                <Text style={[styles.chartTitle, { color: '#CC00FF' }]}>Elevation</Text>
                                <VictoryChart
                                    width={width - 40}
                                    height={220}
                                    theme={VictoryTheme.material}
                                    containerComponent={
                                        <VictoryCursorContainer
                                            cursorDimension="x"
                                            cursorLabel={({ datum }) => {
                                                if (!datum || !datum.x) return "";
                                                const mins = Math.floor(datum.x / 60);
                                                const secs = Math.floor(datum.x % 60);
                                                return `${Math.round(datum.y)} m\n@ ${mins}:${secs < 10 ? '0' : ''}${secs}`;
                                            }}
                                            cursorLabelComponent={
                                                <VictoryLabel
                                                    style={{ fill: "white", fontSize: 12, fontWeight: "bold" }}
                                                    backgroundStyle={{ fill: "#333", opacity: 0.9, rx: 4 }}
                                                    backgroundPadding={8}
                                                />
                                            }
                                            cursorComponent={
                                                <VictoryLine style={{ data: { stroke: "#CC00FF", strokeWidth: 1, strokeDasharray: "4, 4" } }} />
                                            }
                                        />
                                    }
                                >
                                    <Defs>
                                        <LinearGradient id="elevationGradient" x1="0" y1="0" x2="0" y2="1">
                                            <Stop offset="0%" stopColor="#CC00FF" stopOpacity={0.8} />
                                            <Stop offset="100%" stopColor="#6600FF" stopOpacity={0.2} />
                                        </LinearGradient>
                                    </Defs>
                                    <VictoryArea
                                        data={elevationData}
                                        interpolation="step"
                                        style={{
                                            data: { fill: "url(#elevationGradient)", stroke: "#CC00FF", strokeWidth: 2 }
                                        }}
                                    />
                                    <VictoryAxis
                                        style={{
                                            axis: { stroke: "#333" },
                                            tickLabels: { fill: "#666", fontSize: 10 },
                                            grid: { stroke: "#222", strokeWidth: 1 }
                                        }}
                                        tickFormat={(t) => {
                                            const mins = Math.floor(t / 60);
                                            return `${mins}m`;
                                        }}
                                    />
                                    <VictoryAxis
                                        dependentAxis
                                        style={{
                                            axis: { stroke: "transparent" },
                                            tickLabels: { fill: "#666", fontSize: 10 },
                                            grid: { stroke: "#222", strokeDasharray: "4, 4" }
                                        }}
                                    />
                                </VictoryChart>
                            </View>
                        </View>
                    )
                }

                <View style={{ height: 40 }} />
            </ScrollView >
        </ErrorBoundary>
    );
};

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        backgroundColor: '#050505',
        padding: 20,
        paddingTop: 60,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
    },
    backButton: {
        padding: 8,
        backgroundColor: '#1A1A1A',
        borderRadius: 8,
    },
    headerTitle: {
        color: 'white',
        fontSize: 18,
        fontWeight: 'bold',
        maxWidth: '70%',
    },
    chartTitle: {
        color: 'white',
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 10,
    },
    dynamicsItem: {
        width: '48%',
        backgroundColor: '#111',
        padding: 12,
        borderRadius: 8,
        marginBottom: 10,
        borderWidth: 1,
        borderColor: '#222',
    },
    dynamicsLabel: {
        color: '#666',
        fontSize: 10,
        fontWeight: 'bold',
        marginBottom: 4,
        letterSpacing: 1,
    },
    dynamicsValue: {
        color: 'white',
        fontSize: 20,
        fontWeight: 'bold',
    },
    summaryCard: {
        backgroundColor: '#1A1A1A',
        padding: 24,
        borderRadius: 20,
        marginBottom: 30,
    },
    date: {
        color: '#888',
        fontSize: 14,
        marginBottom: 4,
    },
    time: {
        color: '#666',
        fontSize: 12,
        marginBottom: 20,
    },
    mainStats: {
        flexDirection: 'row',
        alignItems: 'center',
        width: '100%',
        justifyContent: 'space-around',
    },
    stat: {
        alignItems: 'center',
    },
    statValue: {
        color: '#CCFF00',
        fontSize: 32,
        fontWeight: 'bold',
        marginBottom: 4,
    },
    statLabel: {
        color: '#888',
        fontSize: 12,
        textTransform: 'uppercase',
    },
    statDivider: {
        width: 1,
        height: 40,
        backgroundColor: '#333',
    },
    section: {
        marginBottom: 30,
    },
    sectionTitle: {
        color: '#666',
        fontSize: 14,
        fontWeight: 'bold',
        marginBottom: 16,
        textTransform: 'uppercase',
        letterSpacing: 1,
    },
    grid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 12,
    },
    metricItem: {
        width: '48%',
        backgroundColor: '#111',
        padding: 16,
        borderRadius: 12,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    iconBox: {
        width: 32,
        height: 32,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    metricLabel: {
        color: '#666',
        fontSize: 10,
        marginBottom: 2,
    },
    metricValue: {
        color: 'white',
        fontSize: 16,
        fontWeight: 'bold',
    },
    metricUnit: {
        fontSize: 10,
        color: '#666',
        fontWeight: 'normal',
    },
    mapContainer: {
        width: '100%',
        height: 250,
        backgroundColor: '#111',
        borderRadius: 16,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#222',
        overflow: 'hidden',
    },
    mapText: {
        color: '#444',
        marginTop: 10,
    },
    noDataText: {
        color: '#666',
        fontStyle: 'italic',
    },
    chartCard: {
        backgroundColor: '#111',
        borderRadius: 16,
        padding: 16,
        marginBottom: 20,
        alignItems: 'center',
    },
});

export default ActivityDetailScreen;
