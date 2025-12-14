import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { ChevronLeft, Calendar, TrendingUp, Flame, Zap } from 'lucide-react-native';

interface DayData {
    date: string;
    tss: number;
    ctl: number;
    atl: number;
    tsb: number;
}

interface Activity {
    id: number;
    name: string;
    date: string;
    distance: number;
    duration: number;
    tss: number;
}

const WeekDetailScreen = () => {
    const navigation = useNavigation<any>();
    const route = useRoute<any>();
    const { startDate, endDate, weekLabel } = route.params;

    const [loading, setLoading] = useState(true);
    const [dailyData, setDailyData] = useState<DayData[]>([]);
    const [activities, setActivities] = useState<Activity[]>([]);

    useEffect(() => {
        fetchWeekData();
    }, []);

    const fetchWeekData = async () => {
        try {
            // Fetch CTL/ATL history for the week
            const pmcRes = await fetch('http://localhost:8000/ingestion/training-load/weekly');
            const pmcData = await pmcRes.json();

            // Filter history for this week's dates
            const weekDays = pmcData.ctl_atl_history?.filter((d: any) =>
                d.date >= startDate && d.date <= endDate
            ) || [];
            setDailyData(weekDays);

            // Fetch activities for this week
            const actRes = await fetch('http://localhost:8000/ingestion/activities?limit=100');
            const actData = await actRes.json();

            // Filter activities for this week
            const weekActivities = actData.filter((a: any) => {
                const actDate = a.startTimeLocal?.split('T')[0];
                return actDate >= startDate && actDate <= endDate;
            }).map((a: any) => ({
                id: a.activityId,
                name: a.activityName,
                date: a.startTimeLocal?.split('T')[0],
                distance: a.distance ? Math.round(a.distance / 1000 * 10) / 10 : 0,
                duration: a.duration || 0,
                tss: 0 // TODO: Calculate from API
            }));
            setActivities(weekActivities);
        } catch (error) {
            console.error('Failed to fetch week data:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatDuration = (seconds: number) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        return h > 0 ? `${h}h ${m}m` : `${m}m`;
    };

    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        return `${days[d.getDay()]} ${d.getDate()}`;
    };

    // Calculate week summary
    const weekCtl = dailyData.length > 0 ? dailyData[dailyData.length - 1].ctl : 0;
    const weekAtl = dailyData.length > 0 ? dailyData[dailyData.length - 1].atl : 0;
    const weekTsb = weekCtl - weekAtl;
    const totalDistance = activities.reduce((sum, a) => sum + a.distance, 0);
    const totalDuration = activities.reduce((sum, a) => sum + a.duration, 0);

    if (loading) {
        return (
            <View style={styles.container}>
                <ActivityIndicator size="large" color="#CCFF00" />
            </View>
        );
    }

    return (
        <ScrollView style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                    <ChevronLeft color="#CCFF00" size={28} />
                </TouchableOpacity>
                <View>
                    <Text style={styles.title}>{weekLabel || 'Week Detail'}</Text>
                    <Text style={styles.subtitle}>{startDate} → {endDate}</Text>
                </View>
            </View>

            {/* Week Summary Cards */}
            <View style={styles.summaryRow}>
                <View style={styles.summaryCard}>
                    <TrendingUp color="#00CCFF" size={20} />
                    <Text style={styles.summaryValue}>{Math.round(weekCtl)}</Text>
                    <Text style={styles.summaryLabel}>Fitness</Text>
                </View>
                <View style={styles.summaryCard}>
                    <Flame color="#FF6600" size={20} />
                    <Text style={[styles.summaryValue, { color: '#FF6600' }]}>{Math.round(weekAtl)}</Text>
                    <Text style={styles.summaryLabel}>Fatigue</Text>
                </View>
                <View style={styles.summaryCard}>
                    <Zap color={weekTsb > 0 ? '#CCFF00' : '#FF3333'} size={20} />
                    <Text style={[styles.summaryValue, { color: weekTsb > 0 ? '#CCFF00' : '#FF3333' }]}>
                        {weekTsb > 0 ? '+' : ''}{Math.round(weekTsb)}
                    </Text>
                    <Text style={styles.summaryLabel}>Form</Text>
                </View>
            </View>

            {/* Total Stats */}
            <View style={styles.statsRow}>
                <View style={styles.statItem}>
                    <Text style={styles.statValue}>{Math.round(totalDistance * 10) / 10} km</Text>
                    <Text style={styles.statLabel}>Total Distance</Text>
                </View>
                <View style={styles.statItem}>
                    <Text style={styles.statValue}>{formatDuration(totalDuration)}</Text>
                    <Text style={styles.statLabel}>Total Time</Text>
                </View>
                <View style={styles.statItem}>
                    <Text style={styles.statValue}>{activities.length}</Text>
                    <Text style={styles.statLabel}>Activities</Text>
                </View>
            </View>

            {/* Daily CTL/ATL Chart */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>📊 Daily Progression</Text>
                <View style={styles.dailyChart}>
                    {dailyData.map((day, idx) => {
                        const maxVal = Math.max(...dailyData.map(d => Math.max(d.ctl, d.atl)), 50);
                        const ctlH = (day.ctl / maxVal) * 50;
                        const atlH = (day.atl / maxVal) * 50;
                        return (
                            <View key={day.date} style={styles.dayBar}>
                                <View style={styles.barsContainer}>
                                    <View style={[styles.ctlBar, { height: ctlH }]} />
                                    <View style={[styles.atlBar, { height: atlH }]} />
                                </View>
                                <Text style={styles.dayLabel}>{formatDate(day.date)}</Text>
                            </View>
                        );
                    })}
                </View>
            </View>

            {/* Activities List */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>🏃 Activities</Text>
                {activities.length === 0 ? (
                    <Text style={styles.noData}>No activities this week</Text>
                ) : (
                    activities.map((act) => (
                        <TouchableOpacity
                            key={act.id}
                            style={styles.activityItem}
                            onPress={() => navigation.navigate('ActivityDetail', { activityId: act.id })}
                        >
                            <View>
                                <Text style={styles.activityName}>{act.name}</Text>
                                <Text style={styles.activityDate}>{formatDate(act.date)}</Text>
                            </View>
                            <View style={styles.activityStats}>
                                <Text style={styles.activityDistance}>{act.distance} km</Text>
                                <Text style={styles.activityDuration}>{formatDuration(act.duration)}</Text>
                            </View>
                        </TouchableOpacity>
                    ))
                )}
            </View>

            <View style={{ height: 40 }} />
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        padding: 16,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 20,
        paddingTop: 40,
    },
    backButton: {
        marginRight: 12,
        padding: 4,
    },
    title: {
        color: '#CCFF00',
        fontSize: 24,
        fontWeight: 'bold',
    },
    subtitle: {
        color: '#666',
        fontSize: 12,
        marginTop: 2,
    },
    summaryRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 16,
    },
    summaryCard: {
        flex: 1,
        backgroundColor: '#111',
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
        marginHorizontal: 4,
    },
    summaryValue: {
        color: '#00CCFF',
        fontSize: 28,
        fontWeight: 'bold',
        marginTop: 8,
    },
    summaryLabel: {
        color: '#666',
        fontSize: 11,
        marginTop: 4,
    },
    statsRow: {
        flexDirection: 'row',
        backgroundColor: '#0A0A0A',
        borderRadius: 12,
        padding: 16,
        marginBottom: 20,
    },
    statItem: {
        flex: 1,
        alignItems: 'center',
    },
    statValue: {
        color: '#FFF',
        fontSize: 18,
        fontWeight: 'bold',
    },
    statLabel: {
        color: '#666',
        fontSize: 10,
        marginTop: 4,
    },
    section: {
        backgroundColor: '#111',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16,
    },
    sectionTitle: {
        color: '#FFF',
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 12,
    },
    dailyChart: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'flex-end',
        height: 80,
    },
    dayBar: {
        alignItems: 'center',
        flex: 1,
    },
    barsContainer: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        height: 55,
    },
    ctlBar: {
        width: 8,
        backgroundColor: 'rgba(0, 204, 255, 0.7)',
        borderRadius: 2,
        marginRight: 2,
    },
    atlBar: {
        width: 8,
        backgroundColor: 'rgba(255, 102, 0, 0.7)',
        borderRadius: 2,
    },
    dayLabel: {
        color: '#555',
        fontSize: 9,
        marginTop: 4,
    },
    noData: {
        color: '#666',
        textAlign: 'center',
        padding: 20,
    },
    activityItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#222',
    },
    activityName: {
        color: '#FFF',
        fontSize: 14,
        fontWeight: '500',
    },
    activityDate: {
        color: '#666',
        fontSize: 11,
        marginTop: 2,
    },
    activityStats: {
        alignItems: 'flex-end',
    },
    activityDistance: {
        color: '#CCFF00',
        fontSize: 14,
        fontWeight: 'bold',
    },
    activityDuration: {
        color: '#888',
        fontSize: 11,
    },
});

export default WeekDetailScreen;
