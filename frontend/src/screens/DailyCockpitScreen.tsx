import React, { useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, useWindowDimensions, TouchableOpacity } from 'react-native';
import { useDashboardStore } from '../store/useDashboardStore';
import { Battery, Zap, Activity, TrendingUp, AlertTriangle, ChevronRight, Play } from 'lucide-react-native';
import { useNavigation } from '@react-navigation/native';

const MetricCard = ({ title, value, subtext, icon: Icon, color, style }: any) => (
    <View style={[styles.card, style]}>
        <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>{title}</Text>
            <Icon size={16} color={color} />
        </View>
        <Text style={[styles.cardValue, { color }]}>{value}</Text>
        <Text style={styles.cardSubtext}>{subtext}</Text>
    </View>
);

const DailyCockpitScreen = () => {
    const navigation = useNavigation<any>();
    const store = useDashboardStore();
    const userProfile = useDashboardStore(state => state.userProfile);
    const activities = useDashboardStore(state => state.activities);
    const setActivities = useDashboardStore(state => state.setActivities);
    const { width } = useWindowDimensions();
    const isDesktop = width > 768;

    useEffect(() => {
        // Fetch activities if empty
        if (activities.length === 0) {
            fetch('http://localhost:8000/ingestion/activities?limit=3')
                .then(res => {
                    if (!res.ok) throw new Error('Failed to fetch activities');
                    return res.json();
                })
                .then(data => setActivities(data))
                .catch(err => {
                    console.error('Activity Fetch Error:', err);
                    // Optionally set empty activities to avoid crash if data structure is expected
                    setActivities([]);
                });
        }
    }, []);

    const getReadinessColor = (score: number) => {
        if (score >= 80) return '#CCFF00'; // Green
        if (score >= 50) return '#FFCC00'; // Yellow
        return '#FF3333'; // Red
    };

    const readinessColor = getReadinessColor(store.readinessScore);

    return (
        <View style={styles.container}>
            <ScrollView contentContainerStyle={styles.scrollContent}>
                <View style={styles.content}>

                    {/* Header */}
                    <View style={styles.header}>
                        <View>
                            <Text style={styles.headerLabel}>TODAY</Text>
                            <Text style={styles.headerTitle}>Daily Cockpit</Text>
                        </View>
                        <View style={[styles.circle, { borderColor: readinessColor }]}>
                            <Activity size={20} color={readinessColor} />
                        </View>
                    </View>

                    {/* Adaptation Banner */}
                    {store.adaptation?.active && (
                        <View style={styles.banner}>
                            <AlertTriangle size={24} color="#FF3333" />
                            <View style={styles.bannerContent}>
                                <Text style={styles.bannerTitle}>Plan Adapted</Text>
                                <Text style={styles.bannerText}>{store.adaptation.reason}</Text>
                                <Text style={styles.bannerSubtext}>{store.adaptation.change}</Text>
                            </View>
                        </View>
                    )}

                    {/* Responsive Grid */}
                    <View style={[styles.gridContainer, isDesktop && styles.gridContainerDesktop]}>

                        {/* Left Column: Metrics */}
                        <View style={[styles.column, isDesktop && styles.columnLeft]}>
                            {/* Key Metrics Row */}
                            <View style={styles.row}>
                                <MetricCard
                                    title="Readiness"
                                    value={store.readinessScore}
                                    subtext="Prime State"
                                    icon={Activity}
                                    color={readinessColor}
                                    style={{ flex: 1 }}
                                />
                                <View style={{ width: 12 }} />
                                <MetricCard
                                    title="Form (TSB)"
                                    value={store.tsb > 0 ? `+${store.tsb}` : store.tsb}
                                    subtext="Peaking"
                                    icon={TrendingUp}
                                    color="#00CCFF"
                                    style={{ flex: 1 }}
                                />
                            </View>

                            {/* Body Battery */}
                            <View style={styles.card}>
                                <View style={styles.cardHeader}>
                                    <Text style={styles.cardTitle}>Body Battery</Text>
                                    <Battery size={16} color={store.bodyBattery > 50 ? '#CCFF00' : '#FF3333'} />
                                </View>
                                <View style={styles.batteryRow}>
                                    <Text style={styles.cardValue}>{store.bodyBattery}%</Text>
                                    <Text style={styles.cardSubtext}>Charged</Text>
                                </View>
                                <View style={styles.progressBar}>
                                    <View style={[styles.progressFill, { width: `${store.bodyBattery}%`, backgroundColor: store.bodyBattery > 50 ? '#CCFF00' : '#FF3333' }]} />
                                </View>
                            </View>
                        </View>

                        {/* Right Column: Workout */}
                        <View style={[styles.column, isDesktop && styles.columnRight]}>
                            <View style={styles.section}>
                                <Text style={styles.sectionTitle}>Today's Mission</Text>
                                {store.todayWorkout ? (
                                    <View style={[styles.workoutCard, { flex: 1 }]}>
                                        <View style={styles.workoutHeader}>
                                            <Text style={styles.workoutType}>{store.todayWorkout.type}</Text>
                                            <Text style={styles.workoutDuration}>{store.todayWorkout.duration}</Text>
                                        </View>
                                        <Text style={styles.workoutIntensity}>{store.todayWorkout.intensity}</Text>
                                        <Text style={styles.workoutDesc}>{store.todayWorkout.description}</Text>

                                        <View style={{ flex: 1 }} />

                                        <TouchableOpacity style={styles.button} onPress={() => navigation.navigate('LiveActivity')}>
                                            <Play size={20} color="#050505" />
                                            <Text style={styles.buttonText}>Start Workout</Text>
                                        </TouchableOpacity>
                                    </View>
                                ) : (
                                    <View style={styles.card}>
                                        <Text style={styles.textWhite}>Rest Day</Text>
                                    </View>
                                )}
                            </View>
                        </View>

                    </View>

                    {/* Recent Activities */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Recent Activities</Text>
                        {activities.slice(0, 3).map(activity => (
                            <TouchableOpacity
                                key={activity.activityId}
                                style={styles.activityCard}
                                onPress={() => navigation.navigate('ActivityDetail', { activity })}
                            >
                                <View style={[styles.iconBox, { backgroundColor: '#CCFF0020' }]}>
                                    <Activity color="#CCFF00" size={20} />
                                </View>
                                <View style={{ flex: 1 }}>
                                    <Text style={styles.activityName}>{activity.activityName}</Text>
                                    <Text style={styles.activityMeta}>
                                        {new Date(activity.startTimeLocal).toLocaleDateString()} • {(activity.distance / 1000).toFixed(1)} km
                                    </Text>
                                </View>
                                <ChevronRight color="#666" size={20} />
                            </TouchableOpacity>
                        ))}
                        {activities.length === 0 && (
                            <Text style={{ color: '#666', fontStyle: 'italic' }}>No recent activities found.</Text>
                        )}
                    </View>
                </View>
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        width: '100%',
        overflow: 'hidden',
    },
    scrollContent: {
        flexGrow: 1,
        width: '100%',
    },
    content: {
        width: '100%',
        padding: 20,
        gap: 20,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10,
    },
    headerLabel: {
        color: '#999',
        fontSize: 12,
        fontWeight: '600',
        marginBottom: 4,
    },
    headerTitle: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
    },
    circle: {
        width: 40,
        height: 40,
        borderRadius: 20,
        borderWidth: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
    gridContainer: {
        flexDirection: 'column',
        gap: 20,
    },
    gridContainerDesktop: {
        flexDirection: 'row',
        alignItems: 'stretch',
    },
    column: {
        flex: 1,
        gap: 20,
    },
    columnLeft: {
        flex: 1,
    },
    columnRight: {
        flex: 1,
    },
    row: {
        flexDirection: 'row',
        gap: 12,
    },
    card: {
        backgroundColor: '#111',
        borderRadius: 12,
        padding: 16,
        borderWidth: 1,
        borderColor: '#333',
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    cardTitle: {
        color: '#999',
        fontSize: 12,
    },
    cardValue: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 4,
    },
    cardSubtext: {
        color: '#666',
        fontSize: 12,
    },
    banner: {
        backgroundColor: '#331100',
        borderColor: '#FF3333',
        borderWidth: 1,
        borderRadius: 12,
        padding: 12,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    bannerContent: {
        flex: 1,
    },
    bannerTitle: {
        color: '#FF3333',
        fontWeight: 'bold',
        marginBottom: 4,
    },
    bannerText: {
        color: 'white',
        fontSize: 14,
        marginBottom: 2,
    },
    bannerSubtext: {
        color: '#999',
        fontSize: 12,
    },
    batteryRow: {
        flexDirection: 'row',
        alignItems: 'baseline',
        gap: 8,
        marginBottom: 12,
    },
    progressBar: {
        height: 4,
        backgroundColor: '#333',
        borderRadius: 2,
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
    },
    section: {
        flex: 1,
        gap: 12,
    },
    sectionTitle: {
        color: 'white',
        fontSize: 18,
        fontWeight: 'bold',
    },
    workoutCard: {
        backgroundColor: '#111',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#333',
        overflow: 'hidden',
    },
    workoutHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        padding: 16,
        paddingBottom: 8,
    },
    workoutType: {
        color: '#CCFF00',
        fontWeight: 'bold',
    },
    workoutDuration: {
        color: 'white',
    },
    workoutIntensity: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
        paddingHorizontal: 16,
        marginBottom: 8,
    },
    workoutDesc: {
        color: '#999',
        paddingHorizontal: 16,
        marginBottom: 16,
    },
    button: {
        backgroundColor: '#CCFF00',
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 16,
        gap: 8,
    },
    buttonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
    },
    textWhite: {
        color: 'white',
    },
    activityCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        padding: 16,
        borderRadius: 12,
        marginBottom: 10,
        gap: 12,
    },
    iconBox: {
        width: 36,
        height: 36,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    activityName: {
        color: 'white',
        fontSize: 14,
        fontWeight: '600',
    },
    activityMeta: {
        color: '#888',
        fontSize: 12,
        marginTop: 2,
    },
});

export default DailyCockpitScreen;
