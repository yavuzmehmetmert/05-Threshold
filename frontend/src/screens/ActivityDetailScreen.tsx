import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Dimensions } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Activity, ArrowUp, Battery, Brain, Calendar, ChevronLeft, Clock, Droplets, Flame, Footprints, Gauge, Heart, MapPin, Moon, Mountain, Move, Shield, Share2, Thermometer, Timer, TrendingUp, Wind, Zap } from 'lucide-react-native';
import { VictoryChart, VictoryLine, VictoryAxis, VictoryTheme, VictoryArea, VictoryScatter, VictoryBar, VictoryVoronoiContainer, VictoryTooltip, VictoryLabel, VictoryCursorContainer } from 'victory-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring, withRepeat, withTiming, interpolateColor, FadeInDown } from 'react-native-reanimated';
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

// --------------------------------------------------------------------------------
// AI INSIGHT COMPONENT ("THE WIPE ANALYSIS")
// --------------------------------------------------------------------------------
const AIInsightCard = ({ type, data }: { type: 'HIIT' | 'ENDURANCE' | 'RECOVERY' | 'FATIGUED_THRESHOLD' | 'BASE'; data: any }) => {
    // Shared Animations
    const pulse = useSharedValue(1);
    const springVal = useSharedValue(0);

    React.useEffect(() => {
        if (type === 'HIIT' || type === 'FATIGUED_THRESHOLD') {
            pulse.value = withRepeat(withTiming(1.1, { duration: 800 }), -1, true);
        } else if (type === 'RECOVERY') {
            springVal.value = withRepeat(withSpring(1, { damping: 5, stiffness: 80 }), -1, true);
        }
    }, [type]);

    const pulseStyle = useAnimatedStyle(() => ({ transform: [{ scale: pulse.value }] }));
    const springStyle = useAnimatedStyle(() => ({
        transform: [{ translateY: springVal.value * 20 }],
        height: 60 - (springVal.value * 10)
    }));

    if (type === 'HIIT' || type === 'FATIGUED_THRESHOLD') {
        const isFatigued = type === 'FATIGUED_THRESHOLD';
        return (
            <View style={[styles.insightCard, { borderColor: isFatigued ? '#FF9900' : '#FF3333', backgroundColor: isFatigued ? '#FF990010' : '#FF333310' }]}>
                <View style={styles.insightHeader}>
                    <Flame color={isFatigued ? '#FF9900' : '#FF3333'} size={24} />
                    <Text style={[styles.insightTitle, { color: isFatigued ? '#FF9900' : '#FF3333' }]}>
                        {isFatigued ? 'HIGH EXERTION (FATIGUED)' : 'HIIT / ANAEROBIC'}
                    </Text>
                </View>

                <View style={styles.insightContent}>
                    {/* Zone 5 Pulse Visual */}
                    <View style={{ alignItems: 'center', width: 80 }}>
                        <Animated.View style={[{ width: 60, height: 60, borderRadius: 30, backgroundColor: isFatigued ? '#FF9900' : '#FF3333', justifyContent: 'center', alignItems: 'center' }, pulseStyle]}>
                            <Text style={{ color: '#000', fontWeight: 'bold' }}>{isFatigued ? 'RPE' : 'Z5'}</Text>
                        </Animated.View>
                        <Text style={styles.insightLabel}>{isFatigued ? 'Grinding' : 'Max Effort'}</Text>
                    </View>

                    <View style={{ flex: 1, paddingLeft: 16 }}>
                        <Text style={styles.insightText}>
                            {isFatigued
                                ? "You pushed hard despite low readiness. Internal load was higher than data suggests due to fatigue."
                                : "High Central Nervous System Load. Your heart spent substantial time in Zone 5."}
                        </Text>
                        <View style={styles.insightStatRow}>
                            <Text style={styles.insightStatLabel}>Load Benefit:</Text>
                            <Text style={styles.insightStatValue}>{isFatigued ? 'Mental Resilience 🧠' : 'VO2 Max 🚀'}</Text>
                        </View>
                        <View style={styles.insightStatRow}>
                            <Text style={styles.insightStatLabel}>Rec. Rest:</Text>
                            <Text style={styles.insightStatValue}>{isFatigued ? '72 Hours' : '48 Hours'}</Text>
                        </View>
                    </View>
                </View>
            </View>
        );
    }

    if (type === 'ENDURANCE') {
        const drift = data.drift || 0;
        return (
            <View style={[styles.insightCard, { borderColor: '#3399FF', backgroundColor: '#3399FF10' }]}>
                <View style={styles.insightHeader}>
                    <Activity color="#3399FF" size={24} />
                    <Text style={[styles.insightTitle, { color: '#3399FF' }]}>AEROBIC ENDURANCE</Text>
                </View>

                <View style={styles.insightContent}>
                    {/* Drift Visual */}
                    <View style={{ alignItems: 'center', width: 80, justifyContent: 'center' }}>
                        <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: 60, gap: 4 }}>
                            <View style={{ width: 8, height: 60, backgroundColor: '#3399FF', borderRadius: 2 }} />
                            {drift > 5 && <View style={{ width: 20, borderBottomWidth: 1, borderColor: '#FF3333' }} />}
                            <View style={{ width: 8, height: drift > 5 ? 40 : 60, backgroundColor: '#FF3333', borderRadius: 2 }} />
                        </View>
                        <Text style={styles.insightLabel}>Drift: {drift.toFixed(1)}%</Text>
                    </View>

                    <View style={{ flex: 1, paddingLeft: 16 }}>
                        <Text style={styles.insightText}>
                            {drift < 5 ? "Diesel Engine Mode. High efficiency with minimal cardiac drift." : "Cardiac Drift detected. Check hydration or pacing."}
                        </Text>
                        <View style={styles.insightStatRow}>
                            <Text style={styles.insightStatLabel}>Engine Rating:</Text>
                            <Text style={styles.insightStatValue}>{drift < 5 ? 'Elite 🚂' : 'Leaky 💧'}</Text>
                        </View>
                    </View>
                </View>
            </View>
        );
    }

    // Recovery Default
    return (
        <View style={[styles.insightCard, { borderColor: '#33FF33', backgroundColor: '#33FF3310' }]}>
            <View style={styles.insightHeader}>
                <Battery color="#33FF33" size={24} />
                <Text style={[styles.insightTitle, { color: '#33FF33' }]}>RECOVERY / BASE</Text>
            </View>

            <View style={styles.insightContent}>
                {/* Mechanic Spring Visual */}
                <View style={{ alignItems: 'center', width: 80, height: 80, justifyContent: 'center' }}>
                    <Animated.View style={[{ width: 20, backgroundColor: '#33FF33', borderRadius: 10 }, springStyle]} />
                    <View style={{ width: 60, height: 2, backgroundColor: '#fff', marginTop: 4 }} />
                    <Text style={styles.insightLabel}>Stiffness</Text>
                </View>

                <View style={{ flex: 1, paddingLeft: 16 }}>
                    <Text style={styles.insightText}>
                        Tissue regeneration focus. Low cardiovascular tax allow form calibration.
                    </Text>
                    <View style={styles.insightStatRow}>
                        <Text style={styles.insightStatLabel}>Repair Status:</Text>
                        <Text style={styles.insightStatValue}>Optimal 🌿</Text>
                    </View>
                </View>
            </View>
        </View>
    );
};

const ActivityDetailScreen = () => {
    const navigation = useNavigation();
    const route = useRoute<any>();
    const { activity } = route.params;
    const isMock = false; // activity.activityId < 1000;
    const [details, setDetails] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [weather, setWeather] = useState(activity.weather || null);
    const [sleepData, setSleepData] = useState<any>(null);
    const [hrvData, setHrvData] = useState<any>(null);

    useEffect(() => {
        fetchActivityDetails();
        fetchSleepData();
        fetchHrvData();
    }, []);

    const fetchHrvData = async () => {
        try {
            const dateStr = activity.startTimeLocal.split(' ')[0];
            const response = await fetch(`http://localhost:8000/ingestion/hrv/${dateStr}`);
            const json = await response.json();
            if (json) {
                setHrvData(json);
            }
        } catch (error) {
            console.error('Failed to fetch HRV data:', error);
        }
    };

    const fetchSleepData = async () => {
        try {
            // Extract YYYY-MM-DD from activity.startTimeLocal (e.g., "2025-12-09 17:54:23")
            const dateStr = activity.startTimeLocal.split(' ')[0];
            const response = await fetch(`http://localhost:8000/ingestion/sleep/${dateStr}`);
            const json = await response.json();
            if (json.dailySleepDTO) {
                setSleepData(json.dailySleepDTO);
            }
        } catch (error) {
            console.error('Failed to fetch sleep data:', error);
        }
    };

    const fetchActivityDetails = async () => {
        try {
            const response = await fetch(`http://localhost:8000/ingestion/activity/${activity.activityId}`);
            const json = await response.json();

            let fitData = [];

            // Handle new API structure { data: [...], weather: {...} }
            if (!Array.isArray(json) && json.data) {
                fitData = json.data;
                if (json.weather) {
                    setWeather(json.weather);
                }
            } else if (Array.isArray(json)) {
                // Fallback for old/mock response
                fitData = json;
            }

            if (fitData.length > 0) {
                setDetails(fitData);
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
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
    };

    const formatPace = (speed: number) => {
        if (!speed || speed === 0) return '-:--';
        // Speed is in m/s (Garmin Standard)
        // Pace (min/km) = (1000 / speed) / 60
        const secondsPerKm = 1000 / speed;
        const mins = Math.floor(secondsPerKm / 60);
        const secs = Math.round(secondsPerKm % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
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

    // Heart Rate Zones & Readiness
    const { userProfile, readinessScore } = useDashboardStore();
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

    // Helper for HR Zone Color
    const getZoneColor = (hr: number) => {
        if (hr < hrZones[1]) return '#999999'; // Z1: Grey
        if (hr < hrZones[2]) return '#3399FF'; // Z2: Blue
        if (hr < hrZones[3]) return '#33FF33'; // Z3: Green
        if (hr < hrZones[4]) return '#FFCC00'; // Z4: Yellow
        return '#FF3333';                      // Z5: Red
    };

    // AI Classification Logic
    const classifyActivity = () => {
        if (!details || details.length === 0) return 'BASE';

        // Use Zone Stats
        const z5Pct = zoneStats[4].pct;
        const z4Pct = zoneStats[3].pct;
        const z3Pct = zoneStats[2].pct;
        const avgHr = calcAvg('heart_rate');

        // Context Awareness: Readiness
        const isLowReadiness = readinessScore && readinessScore < 50;

        // Rule 1: True HIIT (Requires High Zone 5)
        if (z5Pct > 15) return 'HIIT';

        // Rule 2: Fatigued Threshold (Moderate-High Intensity + Low Readiness)
        // User felt it was "Hard" but maybe only hit Z3/Z4 because of fatigue ceiling
        if (isLowReadiness && (z4Pct > 20 || z3Pct > 40)) {
            return 'FATIGUED_THRESHOLD';
        }

        // Rule 3: Recovery (Strictly Z1/Z2)
        if (avgHr < hrZones[2] && activity.duration < 3600 && z4Pct < 5) return 'RECOVERY';

        // Default: Aerobic Endurance
        return 'ENDURANCE';
    };

    const activityType = classifyActivity();

    // --- ADVANCED CALCS: Laps & Normalized Power ---
    const calculateAdvancedMetrics = () => {
        if (!details || details.length === 0) return { laps: [], np: 0, work: 0 };

        // 1. Normalized Power (NP)
        // Rolling 30s avg, raised to 4th power
        const rolling30 = [];
        const powers = details.map(d => d.power || 0);

        for (let i = 0; i < powers.length; i++) {
            // Get 30s window ending at i
            const start = Math.max(0, i - 29);
            const window = powers.slice(start, i + 1);
            const avg = window.reduce((a, b) => a + b, 0) / window.length;
            rolling30.push(avg);
        }

        const sumPow4 = rolling30.reduce((acc, curr) => acc + Math.pow(curr, 4), 0);
        const avgPow4 = sumPow4 / rolling30.length;
        const np = Math.round(Math.pow(avgPow4, 0.25));

        // Total Work (kJ) = Avg Power * Seconds / 1000
        const avgPwr = powers.reduce((a, b) => a + b, 0) / powers.length;
        const work = Math.round((avgPwr * activity.duration) / 1000);

        // 2. Auto-Laps (1km Splits)
        interface Lap {
            id: number;
            distance: string;
            time: string;
            pace: string;
            hr: number;
            power: number;
            elevation: number;
        }
        const laps: Lap[] = [];
        let lapStartIdx = 0;
        let nextKm = 1000;

        // Find split points
        details.forEach((d, i) => {
            if (d.distance >= nextKm || i === details.length - 1) {
                // Determine Lap Segments
                const chunk = details.slice(lapStartIdx, i + 1);
                if (chunk.length > 0) {
                    const lapDist = chunk[chunk.length - 1].distance - (chunk[0].distance || 0); // approx
                    const duration = (new Date(chunk[chunk.length - 1].timestamp).getTime() - new Date(chunk[0].timestamp).getTime()) / 1000;

                    // Elevation Math
                    const startElev = chunk[0].altitude || 0;
                    const endElev = chunk[chunk.length - 1].altitude || 0;
                    const elevDiff = Math.round(endElev - startElev);

                    if (duration > 0) {
                        const avgPace = duration / (lapDist / 1000); // sec/km
                        const lapAvgHr = Math.round(chunk.reduce((a, c) => a + (c.heart_rate || 0), 0) / chunk.length);
                        const lapAvgPwr = Math.round(chunk.reduce((a, c) => a + (c.power || 0), 0) / chunk.length);

                        const m = Math.floor(avgPace / 60);
                        const s = Math.round(avgPace % 60);

                        laps.push({
                            id: laps.length + 1,
                            distance: (lapDist / 1000).toFixed(2),
                            time: formatDuration(duration),
                            pace: `${m}:${s < 10 ? '0' : ''}${s}`,
                            hr: lapAvgHr,
                            power: lapAvgPwr,
                            elevation: elevDiff
                        });
                    }
                }
                lapStartIdx = i;
                nextKm += 1000;
            }
        });

        // 3. Smoothed Power for Chart (10s Avg)
        const smoothedPower: { x: number; y: number }[] = [];
        for (let i = 0; i < powers.length; i++) {
            const start = Math.max(0, i - 9);
            const win = powers.slice(start, i + 1);
            const avg = win.reduce((a, b) => a + b, 0) / win.length;
            smoothedPower.push({ x: i, y: avg });
        }

        return { laps, np, work, smoothedPower };
    };

    const { laps, np, work, smoothedPower } = calculateAdvancedMetrics();


    return (
        <ErrorBoundary>
            <ScrollView contentContainerStyle={styles.container}>
                <View style={styles.header}>
                    <View style={styles.headerContent}>
                        <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
                            <ChevronLeft color="#fff" size={24} />
                        </TouchableOpacity>
                        <Text style={styles.headerTitle} numberOfLines={1}>{activity.activityName}</Text>
                        <View style={{ width: 24 }} />
                    </View>
                    <Text style={styles.date}>{new Date(activity.startTimeLocal).toLocaleDateString()} • {new Date(activity.startTimeLocal).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text>
                    <Text style={styles.title}>{activity.activityName}</Text>

                    {/* Weather Context Strip */}
                    {weather && (
                        <View style={styles.weatherStrip}>
                            <View style={styles.weatherItem}>
                                <Thermometer size={14} color="#888" />
                                <Text style={styles.weatherText}>{weather.temp}°C</Text>
                            </View>
                            <View style={styles.weatherItem}>
                                <Wind size={14} color="#888" />
                                <Text style={styles.weatherText}>{weather.windSpeed} km/h</Text>
                            </View>
                            <View style={styles.weatherItem}>
                                <Droplets size={14} color="#888" />
                                <Text style={styles.weatherText}>{weather.humidity}%</Text>
                            </View>
                            <View style={styles.weatherItem}>
                                <Activity size={14} color="#888" />
                                <Text style={styles.weatherText}>AQI {weather.aqi}</Text>
                            </View>
                            {weather.elevation && (
                                <View style={styles.weatherItem}>
                                    <Mountain size={14} color="#888" />
                                    <Text style={styles.weatherText}>{weather.elevation}m</Text>
                                </View>
                            )}
                        </View>
                    )}

                    <View style={styles.mainStatsRow}>
                        <View style={styles.statItem}>
                            <Text style={styles.statLabel}>Distance</Text>
                            <Text style={styles.statValue}>{(activity.distance / 1000).toFixed(2)} <Text style={styles.unit}>km</Text></Text>
                        </View>
                        <View style={styles.statItem}>
                            <Text style={styles.statLabel}>Duration</Text>
                            <Text style={styles.statValue}>{formatDuration(activity.duration)}</Text>
                        </View>
                        <View style={styles.statItem}>
                            <Text style={styles.statLabel}>Avg Pace</Text>
                            <Text style={styles.statValue}>{formatPace(activity.avgSpeed)} <Text style={styles.unit}>/km</Text></Text>
                        </View>
                    </View>
                </View>

                {/* --- RECOVERY CONTEXT (SLEEP & HRV) --- */}
                <Animated.View entering={FadeInDown.delay(300).duration(600).springify()} style={{ paddingHorizontal: 16, marginTop: 10 }}>
                    <View style={{ flexDirection: 'row', gap: 12 }}>
                        {/* Sleep Card */}
                        <View style={{ flex: 1, backgroundColor: '#111', borderRadius: 16, padding: 12, borderWidth: 1, borderColor: '#222' }}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                                <Moon size={16} color="#9F7AEA" />
                                <Text style={{ color: '#888', fontSize: 12, fontWeight: '600', marginLeft: 6 }}>SLEEP</Text>
                            </View>

                            {sleepData ? (
                                <View>
                                    <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 4 }}>
                                        <Text style={{ color: '#fff', fontSize: 24, fontWeight: 'bold' }}>
                                            {formatDuration(sleepData.sleepTimeSeconds)}
                                        </Text>
                                    </View>
                                    <Text style={{ color: sleepData.sleepScores?.overall?.value > 80 ? '#33FF33' : '#FFCC00', fontSize: 13, fontWeight: '500', marginTop: 4 }}>
                                        Score: {sleepData.sleepScores?.overall?.value || '-'}
                                    </Text>

                                    {/* Sleep Stages Bar */}
                                    <View style={{ flexDirection: 'row', height: 6, borderRadius: 3, overflow: 'hidden', marginTop: 8, width: '100%' }}>
                                        <View style={{ flex: sleepData.deepSleepSeconds, backgroundColor: '#553C9A' }} />
                                        <View style={{ flex: sleepData.lightSleepSeconds, backgroundColor: '#9F7AEA' }} />
                                        <View style={{ flex: sleepData.remSleepSeconds, backgroundColor: '#38B2AC' }} />
                                    </View>
                                    <View style={{ flexDirection: 'row', gap: 6, marginTop: 4 }}>
                                        <Text style={{ fontSize: 8, color: '#553C9A' }}>Deep</Text>
                                        <Text style={{ fontSize: 8, color: '#9F7AEA' }}>Light</Text>
                                        <Text style={{ fontSize: 8, color: '#38B2AC' }}>REM</Text>
                                    </View>
                                </View>
                            ) : (
                                <ActivityIndicator size="small" color="#9F7AEA" />
                            )}
                        </View>

                        {/* HRV Card */}
                        <View style={{ flex: 1, backgroundColor: '#111', borderRadius: 16, padding: 12, borderWidth: 1, borderColor: '#222' }}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                                <Activity size={16} color="#38B2AC" />
                                <Text style={{ color: '#888', fontSize: 12, fontWeight: '600', marginLeft: 6 }}>HRV (Night)</Text>
                            </View>
                            {hrvData ? (
                                <>
                                    <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 4 }}>
                                        <Text style={{ color: '#fff', fontSize: 24, fontWeight: 'bold' }}>
                                            {hrvData.hrvSummary?.lastNightAvg || '-'}ms
                                        </Text>
                                    </View>
                                    <Text style={{ color: '#38B2AC', fontSize: 13, fontWeight: '500', marginTop: 4 }}>
                                        {hrvData.hrvSummary?.status || 'Balanced'}
                                    </Text>
                                </>
                            ) : (
                                <ActivityIndicator size="small" color="#38B2AC" />
                            )}
                        </View>
                    </View>
                </Animated.View>

                {/* --- AI INSIGHT CARD (THE WIPE ANALYSIS) --- */}
                {!loading && (
                    <Animated.View entering={FadeInDown.delay(400).duration(600).springify()} style={{ padding: 16, paddingBottom: 0 }}>
                        <AIInsightCard type={activityType} data={{ drift: cardiacDrift }} />
                    </Animated.View>
                )}

                {/* --- ANALYTICS CONTENT --- */}
                <View style={styles.analyticsContainer}>
                    {/* Activity Map (Interactive) */}
                    <Animated.View entering={FadeInDown.delay(200).duration(800)} style={[styles.section, { marginBottom: 20 }]}>
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
                    </Animated.View>


                    {/* Removed Old Route Visualization */}

                    {/* Detailed Metrics Grid */}
                    <Animated.View entering={FadeInDown.delay(600).springify()} style={styles.section}>
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
                                value={activity.elevationGain || (() => {
                                    if (!details || details.length < 2) return 0;
                                    let gain = 0;
                                    for (let i = 1; i < details.length; i++) {
                                        const diff = (details[i].altitude || 0) - (details[i - 1].altitude || 0);
                                        if (diff > 0) gain += diff;
                                    }
                                    return Math.round(gain);
                                })()}
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
                    </Animated.View>

                    {/* Advanced Training Load Grid */}
                    <View style={[styles.section, { marginTop: 20 }]}>
                        <Text style={styles.sectionTitle}>Training Load</Text>
                        <View style={styles.grid}>
                            <MetricItem
                                icon={Zap}
                                label="Norm. Power"
                                value={np || '-'}
                                unit="W"
                                color="#FFCC00"
                            />
                            <MetricItem
                                icon={Activity}
                                label="Work"
                                value={work || '-'}
                                unit="kJ"
                                color="#FF3333"
                            />
                            {/* IF and TSS would go here if FTP is known */}
                            <MetricItem
                                icon={Activity}
                                label="Intensity"
                                value={np > 0 ? (np / 250).toFixed(2) : '-'} // Assuming 250W FTP for now
                                unit="IF"
                                color="#00CCFF"
                            />
                        </View>
                    </View>

                    {/* Laps Table */}
                    {laps.length > 0 && (
                        <View style={[styles.section, { marginTop: 24 }]}>
                            <Text style={[styles.sectionTitle, { marginBottom: 16 }]}>Splits (1km)</Text>
                            <View style={{ backgroundColor: '#1A1A1A', borderRadius: 12, padding: 16, overflow: 'hidden' }}>
                                {/* Header */}
                                <View style={{ flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#333', paddingBottom: 12, marginBottom: 8 }}>
                                    <Text style={{ width: 40, color: '#888', fontSize: 13, fontWeight: '600' }}>Lap</Text>
                                    <Text style={{ flex: 1, color: '#888', fontSize: 13, fontWeight: '600', textAlign: 'center' }}>Pace</Text>
                                    <Text style={{ width: 50, color: '#888', fontSize: 13, fontWeight: '600', textAlign: 'center' }}>HR</Text>
                                    <Text style={{ width: 50, color: '#888', fontSize: 13, fontWeight: '600', textAlign: 'center' }}>Elev</Text>
                                    <Text style={{ width: 50, color: '#888', fontSize: 13, fontWeight: '600', textAlign: 'right' }}>Pwr</Text>
                                </View>
                                {laps.map((lap, i) => (
                                    <View key={i} style={{
                                        flexDirection: 'row',
                                        paddingVertical: 12,
                                        borderBottomWidth: i === laps.length - 1 ? 0 : 1,
                                        borderBottomColor: '#2A2A2A',
                                        alignItems: 'center'
                                    }}>
                                        <View style={{ width: 40, justifyContent: 'center' }}>
                                            <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: '#333', justifyContent: 'center', alignItems: 'center' }}>
                                                <Text style={{ color: '#fff', fontSize: 12, fontWeight: 'bold' }}>{lap.id}</Text>
                                            </View>
                                        </View>
                                        <Text style={{ flex: 1, color: '#fff', fontSize: 16, fontWeight: 'bold', fontFamily: 'System', textAlign: 'center' }}>
                                            {lap.pace}
                                        </Text>
                                        <Text style={{ width: 50, color: getZoneColor(lap.hr), fontSize: 15, fontWeight: 'bold', textAlign: 'center' }}>
                                            {lap.hr}
                                        </Text>
                                        <Text style={{ width: 50, color: lap.elevation > 0 ? '#33FF33' : lap.elevation < 0 ? '#FF3333' : '#888', fontSize: 14, fontWeight: '600', textAlign: 'center' }}>
                                            {lap.elevation > 0 ? '+' : ''}{lap.elevation}
                                        </Text>
                                        <Text style={{ width: 50, color: '#FFFF00', fontSize: 15, fontWeight: '600', textAlign: 'right' }}>
                                            {lap.power}
                                        </Text>
                                    </View>
                                ))}
                            </View>
                        </View>
                    )}

                    {/* Elevation Chart */}
                    <View style={[styles.section, { marginBottom: 20 }]}>
                        <Text style={styles.sectionTitle}>Elevation Profile</Text>
                        <View style={styles.chartCard}>
                            <VictoryChart
                                width={width - 40}
                                height={150}
                                theme={VictoryTheme.material}
                            >
                                <VictoryArea
                                    data={elevationData}
                                    style={{ data: { fill: "#CC00FF", fillOpacity: 0.3, stroke: "#CC00FF", strokeWidth: 2 } }}
                                    interpolation="natural"
                                />
                                <VictoryAxis style={{ axis: { stroke: "transparent" }, tickLabels: { fill: "#666", fontSize: 10 } }} />
                            </VictoryChart>
                        </View>
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
                                <MetricItem
                                    icon={Move}
                                    label="GCT Bal."
                                    value={(() => {
                                        const valid = details.filter(d => d.stance_time_balance);
                                        if (valid.length === 0) return '-';
                                        const avg = valid.reduce((acc, curr) => acc + curr.stance_time_balance, 0) / valid.length;
                                        // Garmin standard: value is usually Left %? Or just %?
                                        // Mock data is ~49.5. Let's assume Left %.
                                        return `L ${avg.toFixed(1)}%`;
                                    })()}
                                    unit=""
                                    color="#FF5555"
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




                            {/* Power Chart (New) */}
                            {details.some(d => d.power) && (
                                <View style={styles.chartCard}>
                                    <Text style={[styles.chartTitle, { color: '#FFCC00' }]}>Power (10s Smoothing)</Text>
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
                                                    <VictoryLine style={{ data: { stroke: "#CCFF00", strokeWidth: 1, strokeDasharray: "4, 4" } }} />
                                                }
                                            />
                                        }
                                    >
                                        <Defs>
                                            <LinearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1">
                                                <Stop offset="0%" stopColor="#FFFF00" stopOpacity={0.8} />
                                                <Stop offset="100%" stopColor="#FFFF00" stopOpacity={0.0} />
                                            </LinearGradient>
                                        </Defs>
                                        <VictoryArea
                                            data={smoothedPower}
                                            style={{
                                                data: { fill: "url(#powerGradient)", stroke: "#FFFF00", strokeWidth: 2 }
                                            }}
                                            interpolation="monotoneX" // Smooth curves
                                        />
                                        <VictoryAxis style={{ axis: { stroke: "transparent" }, tickLabels: { fill: "#666", fontSize: 10 } }} />
                                        <VictoryAxis dependentAxis style={{ axis: { stroke: "transparent" }, tickLabels: { fill: "#666", fontSize: 10 }, grid: { stroke: "#333" } }} />
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
        </ErrorBoundary >
    );
};

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        backgroundColor: '#050505',
        paddingTop: 60,
    },
    header: {
        paddingHorizontal: 20,
        marginBottom: 20,
    },
    headerContent: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    dateText: {
        color: '#888',
        fontSize: 12,
        textAlign: 'center',
    },
    analyticsContainer: {
        padding: 16,
    },
    // AI Insight Styles
    insightCard: {
        backgroundColor: '#111',
        borderRadius: 16,
        padding: 16,
        marginBottom: 8,
        borderWidth: 1,
    },
    insightHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 10 },
    insightTitle: { fontSize: 18, fontWeight: 'bold', letterSpacing: 1 },
    insightContent: { flexDirection: 'row', alignItems: 'center' },
    insightLabel: { color: '#888', fontSize: 12, marginTop: 4, textAlign: 'center' },
    insightText: { color: '#ccc', fontSize: 14, marginBottom: 12, lineHeight: 20 },
    insightStatRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
    insightStatLabel: { color: '#666', fontSize: 12 },
    insightStatValue: { color: '#fff', fontWeight: 'bold', fontSize: 14 },

    // Weather Styles
    weatherStrip: {
        flexDirection: 'row',
        marginTop: 8,
        marginBottom: 8,
        gap: 12,
    },
    weatherItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    weatherText: {
        color: '#ccc',
        fontSize: 12,
        fontWeight: '500',
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#fff',
        marginBottom: 8,
    },
    date: {
        color: '#888',
        fontSize: 14,
        marginBottom: 4,
    },
    mainStatsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 16,
    },
    statItem: {
        alignItems: 'center',
    },
    statLabel: {
        color: '#666',
        fontSize: 12,
        marginBottom: 4,
    },
    statValue: {
        color: '#fff',
        fontSize: 20,
        fontWeight: 'bold',
    },
    unit: {
        fontSize: 12,
        color: '#666',
        fontWeight: 'normal',
    },
    gridContainer: {
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
