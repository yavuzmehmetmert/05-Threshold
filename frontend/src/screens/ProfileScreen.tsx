import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, RefreshControl, Modal, TextInput, Alert, Dimensions } from 'react-native';
import { useDashboardStore } from '../store/useDashboardStore';
import { User, RefreshCw, Activity, Heart, Scale, Wind, LogOut, Plus, Trash2, X, TrendingUp, TrendingDown } from 'lucide-react-native';
import { VictoryLine, VictoryChart, VictoryAxis, VictoryVoronoiContainer, VictoryScatter } from 'victory-native';

const { width } = Dimensions.get('window');

// Clickable MetricCard
const MetricCard = ({ icon: Icon, label, value, unit, color, onPress }: any) => (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
        <View style={[styles.iconBox, { backgroundColor: color + '20' }]}>
            <Icon color={color} size={24} />
        </View>
        <View>
            <Text style={styles.cardLabel}>{label}</Text>
            <Text style={styles.cardValue}>{value} <Text style={styles.cardUnit}>{unit}</Text></Text>
        </View>
    </TouchableOpacity>
);

interface ShoeData {
    id: number;
    name: string;
    brand?: string;
    initialDistance: number;
    totalDistance: number;
    isActive: boolean;
}

const ProfileScreen = () => {
    const userProfile = useDashboardStore(state => state.userProfile);
    const goals = useDashboardStore(state => state.goals);
    const updateUserProfile = useDashboardStore(state => state.updateUserProfile);
    const [refreshing, setRefreshing] = useState(false);
    const [debugData, setDebugData] = useState<any>(null);
    const [lastSyncDate, setLastSyncDate] = useState<string | null>(null);

    // Shoes State
    const [shoes, setShoes] = useState<ShoeData[]>([]);
    const [showAddShoe, setShowAddShoe] = useState(false);
    const [newShoeName, setNewShoeName] = useState('');
    const [newShoeBrand, setNewShoeBrand] = useState('');
    const [newShoeInitialKm, setNewShoeInitialKm] = useState('0');

    // Metric Detail Modal State
    const [selectedMetric, setSelectedMetric] = useState<{
        label: string;
        key: string;
        color: string;
        unit: string;
    } | null>(null);
    const [historyData, setHistoryData] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [timeRange, setTimeRange] = useState<'7' | '30' | '90' | '180' | '550'>('30');
    const [selectedPoint, setSelectedPoint] = useState<{ date: string; value: number } | null>(null);

    const timeRangeOptions = [
        { label: '1W', value: '7' as const },
        { label: '1M', value: '30' as const },
        { label: '3M', value: '90' as const },
        { label: '6M', value: '180' as const },
        { label: 'ALL', value: '550' as const },
    ];

    // Fetch historical data
    const fetchHistoryData = async (days: string) => {
        setLoadingHistory(true);
        try {
            const response = await fetch(`http://localhost:8000/ingestion/profile/history?days=${days}`);
            if (response.ok) {
                const data = await response.json();
                setHistoryData(data.reverse()); // Oldest first for chart
            }
        } catch (error) {
            console.error('Fetch history error:', error);
        } finally {
            setLoadingHistory(false);
        }
    };

    // Fetch historical data when metric is selected
    const openMetricDetail = async (metric: { label: string; key: string; color: string; unit: string }) => {
        setSelectedMetric(metric);
        setTimeRange('30'); // Reset to 1 month
        setSelectedPoint(null); // Clear tooltip
        await fetchHistoryData('30');
    };

    // Handle time range change
    const handleTimeRangeChange = async (range: typeof timeRange) => {
        setTimeRange(range);
        setSelectedPoint(null); // Clear tooltip
        await fetchHistoryData(range);
    };

    // Calculate statistics for the metric
    const getMetricStats = (key: string) => {
        const values = historyData
            .map(d => d[key])
            .filter(v => v !== null && v !== undefined);
        if (values.length === 0) return { min: '-', max: '-', avg: '-', trend: 0 };

        const min = Math.min(...values);
        const max = Math.max(...values);
        const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);

        // Calculate trend (last 7 days vs previous 7 days)
        const recent = values.slice(-7);
        const previous = values.slice(-14, -7);
        const recentAvg = recent.length > 0 ? recent.reduce((a: number, b: number) => a + b, 0) / recent.length : 0;
        const prevAvg = previous.length > 0 ? previous.reduce((a: number, b: number) => a + b, 0) / previous.length : 0;
        const trend = prevAvg > 0 ? ((recentAvg - prevAvg) / prevAvg * 100) : 0;

        return { min, max, avg, trend };
    };

    // Fetch profile data from API
    const fetchProfileData = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/profile/latest');
            if (response.ok) {
                const data = await response.json();
                setDebugData(data);
                setLastSyncDate(data.date);
                updateUserProfile({
                    maxHr: data.maxHr,
                    restingHr: data.restingHr,
                    lthr: data.lthr,
                    weight: data.weight,
                    vo2max: data.vo2max,
                    stressScore: data.stressScore,
                });
            }
        } catch (error) {
            console.error('Fetch profile error:', error);
        }
    };

    useEffect(() => {
        fetchProfileData(); // Load profile data on mount
        fetchShoes();
    }, []);

    const fetchShoes = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/shoes');
            if (response.ok) {
                const data = await response.json();
                setShoes(data);
            }
        } catch (error) {
            console.error('Fetch shoes error:', error);
        }
    };

    const addShoe = async () => {
        if (!newShoeName.trim()) {
            Alert.alert('Error', 'Please enter a shoe name');
            return;
        }
        try {
            const response = await fetch('http://localhost:8000/ingestion/shoes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newShoeName,
                    brand: newShoeBrand,
                    initialDistance: parseFloat(newShoeInitialKm) || 0
                })
            });
            if (response.ok) {
                setShowAddShoe(false);
                setNewShoeName('');
                setNewShoeBrand('');
                setNewShoeInitialKm('0');
                fetchShoes();
            }
        } catch (error) {
            console.error('Add shoe error:', error);
        }
    };

    const deleteShoe = async (shoeId: number) => {
        Alert.alert('Retire Shoe', 'Are you sure you want to retire this shoe?', [
            { text: 'Cancel', style: 'cancel' },
            {
                text: 'Retire',
                style: 'destructive',
                onPress: async () => {
                    try {
                        await fetch(`http://localhost:8000/ingestion/shoes/${shoeId}`, { method: 'DELETE' });
                        fetchShoes();
                    } catch (error) {
                        console.error('Delete shoe error:', error);
                    }
                }
            }
        ]);
    };

    const onRefresh = async () => {
        setRefreshing(true);
        try {
            // 1. First trigger a profile sync to update DB with latest Garmin data
            await fetch('http://localhost:8000/ingestion/sync/profile', { method: 'POST' });

            // 2. Then fetch the latest profile data from DB
            const response = await fetch('http://localhost:8000/ingestion/profile/latest');
            if (response.ok) {
                const realData = await response.json();
                setDebugData(realData);
                setLastSyncDate(realData.date);
                updateUserProfile({
                    maxHr: realData.maxHr,
                    restingHr: realData.restingHr,
                    lthr: realData.lthr,
                    weight: realData.weight,
                    vo2max: realData.vo2max,
                    stressScore: realData.stressScore,
                });
            }
            await fetchShoes();
        } catch (error) {
            console.error('Refresh Error:', error);
        } finally {
            setRefreshing(false);
        }
    };

    return (
        <ScrollView
            contentContainerStyle={styles.container}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#CCFF00" />}
        >
            <View style={styles.header}>
                <View style={styles.avatar}>
                    <User color="#050505" size={40} />
                </View>
                <View>
                    <Text style={styles.name}>{userProfile.name || 'Runner'}</Text>
                    <Text style={styles.email}>{userProfile.email || 'Connected via Garmin'}</Text>
                </View>
            </View>

            <View style={styles.section}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <Text style={styles.sectionTitle}>Physiological Profile</Text>
                    {lastSyncDate && (
                        <Text style={{ color: '#666', fontSize: 12 }}>Last Sync: {lastSyncDate}</Text>
                    )}
                </View>
                <View style={styles.grid}>
                    <MetricCard icon={Scale} label="Weight" value={userProfile.weight} unit="kg" color="#CCFF00"
                        onPress={() => openMetricDetail({ label: 'Weight', key: 'weight', color: '#CCFF00', unit: 'kg' })} />
                    <MetricCard icon={Heart} label="Resting HR" value={userProfile.restingHr} unit="bpm" color="#00CCFF"
                        onPress={() => openMetricDetail({ label: 'Resting HR', key: 'restingHr', color: '#00CCFF', unit: 'bpm' })} />
                    <MetricCard icon={Activity} label="Lactate Threshold" value={userProfile.lthr} unit="bpm" color="#FF3333"
                        onPress={() => openMetricDetail({ label: 'Lactate Threshold', key: 'lthr', color: '#FF3333', unit: 'bpm' })} />
                    <MetricCard icon={Wind} label="VO2 Max" value={userProfile.vo2max} unit="ml/kg/min" color="#CC00FF"
                        onPress={() => openMetricDetail({ label: 'VO2 Max', key: 'vo2max', color: '#CC00FF', unit: 'ml/kg/min' })} />
                    <MetricCard icon={Heart} label="Max HR" value={userProfile.maxHr} unit="bpm" color="#FF9900"
                        onPress={() => Alert.alert('Max HR', 'Calculated from age: 220 - your age')} />
                    <MetricCard icon={Activity} label="Stress Score" value={userProfile.stressScore || '-'} unit="/100" color={userProfile.stressScore > 50 ? "#FF3333" : "#00FF99"}
                        onPress={() => openMetricDetail({ label: 'Stress Score', key: 'avgStress', color: '#00FF99', unit: '/100' })} />
                </View>
            </View>

            {/* Shoes Section */}
            <View style={styles.section}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <Text style={styles.sectionTitle}>My Shoes</Text>
                    <TouchableOpacity
                        style={{ backgroundColor: '#CCFF00', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, flexDirection: 'row', alignItems: 'center', gap: 4 }}
                        onPress={() => setShowAddShoe(true)}
                    >
                        <Plus size={16} color="#050505" />
                        <Text style={{ color: '#050505', fontWeight: 'bold', fontSize: 13 }}>Add</Text>
                    </TouchableOpacity>
                </View>

                {shoes.length === 0 ? (
                    <View style={styles.infoCard}>
                        <Text style={{ color: '#666', textAlign: 'center' }}>No shoes added yet</Text>
                    </View>
                ) : (
                    shoes.map(shoe => (
                        <View key={shoe.id} style={[styles.infoCard, { marginBottom: 8, flexDirection: 'row', alignItems: 'center' }]}>
                            <View style={{ flex: 1 }}>
                                <Text style={{ color: 'white', fontWeight: '600', fontSize: 16 }}>{shoe.name}</Text>
                                {shoe.brand && <Text style={{ color: '#888', fontSize: 12 }}>{shoe.brand}</Text>}
                                <View style={{ flexDirection: 'row', marginTop: 8, gap: 16 }}>
                                    <View>
                                        <Text style={{ color: '#666', fontSize: 10 }}>TOTAL KM</Text>
                                        <Text style={{ color: '#CCFF00', fontWeight: 'bold', fontSize: 18 }}>{shoe.totalDistance.toFixed(0)}</Text>
                                    </View>
                                    <View>
                                        <Text style={{ color: '#666', fontSize: 10 }}>INITIAL</Text>
                                        <Text style={{ color: '#888', fontSize: 14 }}>{shoe.initialDistance} km</Text>
                                    </View>
                                </View>
                            </View>
                            <TouchableOpacity onPress={() => deleteShoe(shoe.id)} style={{ padding: 8 }}>
                                <Trash2 size={20} color="#FF3333" />
                            </TouchableOpacity>
                        </View>
                    ))
                )}
            </View>

            {/* Training Context Section */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Training Schedule</Text>
                <View style={styles.infoCard}>
                    <View style={styles.row}>
                        <Text style={styles.label}>Experience</Text>
                        <Text style={styles.value}>{goals.experienceLevel}</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.label}>Training Days</Text>
                        <Text style={styles.value}>
                            {goals.trainingDays.length > 0 ? goals.trainingDays.join(', ') : '-'}
                        </Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.label}>Long Run</Text>
                        <Text style={[styles.value, { color: '#CCFF00' }]}>
                            {goals.longRunDay || '-'}
                        </Text>
                    </View>
                </View>
            </View>

            <TouchableOpacity style={styles.refreshButton} onPress={onRefresh}>
                <RefreshCw color="#050505" size={20} />
                <Text style={styles.refreshButtonText}>Sync from Garmin</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.logoutButton}>
                <LogOut color="#666" size={20} />
                <Text style={styles.logoutButtonText}>Disconnect</Text>
            </TouchableOpacity>

            {/* Add Shoe Modal */}
            <Modal visible={showAddShoe} animationType="slide" transparent>
                <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'center', padding: 20 }}>
                    <View style={{ backgroundColor: '#1A1A1A', borderRadius: 16, padding: 20 }}>
                        <Text style={{ color: 'white', fontSize: 20, fontWeight: 'bold', marginBottom: 20 }}>Add New Shoe</Text>

                        <Text style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>SHOE NAME *</Text>
                        <TextInput
                            style={{ backgroundColor: '#111', color: 'white', padding: 12, borderRadius: 8, marginBottom: 16 }}
                            placeholder="e.g. Nike Pegasus 40"
                            placeholderTextColor="#666"
                            value={newShoeName}
                            onChangeText={setNewShoeName}
                        />

                        <Text style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>BRAND</Text>
                        <TextInput
                            style={{ backgroundColor: '#111', color: 'white', padding: 12, borderRadius: 8, marginBottom: 16 }}
                            placeholder="e.g. Nike"
                            placeholderTextColor="#666"
                            value={newShoeBrand}
                            onChangeText={setNewShoeBrand}
                        />

                        <Text style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>CURRENT MILEAGE (km)</Text>
                        <TextInput
                            style={{ backgroundColor: '#111', color: 'white', padding: 12, borderRadius: 8, marginBottom: 20 }}
                            placeholder="0"
                            placeholderTextColor="#666"
                            keyboardType="numeric"
                            value={newShoeInitialKm}
                            onChangeText={setNewShoeInitialKm}
                        />

                        <View style={{ flexDirection: 'row', gap: 12 }}>
                            <TouchableOpacity
                                style={{ flex: 1, backgroundColor: '#333', padding: 14, borderRadius: 8, alignItems: 'center' }}
                                onPress={() => setShowAddShoe(false)}
                            >
                                <Text style={{ color: '#888', fontWeight: 'bold' }}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={{ flex: 1, backgroundColor: '#CCFF00', padding: 14, borderRadius: 8, alignItems: 'center' }}
                                onPress={addShoe}
                            >
                                <Text style={{ color: '#050505', fontWeight: 'bold' }}>Add Shoe</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            </Modal>

            {/* Metric Detail Modal */}
            <Modal visible={selectedMetric !== null} animationType="slide" transparent>
                <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.9)', justifyContent: 'flex-end' }}>
                    <View style={{ backgroundColor: '#1A1A1A', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40, minHeight: '70%' }}>
                        {/* Header */}
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                            <Text style={{ color: 'white', fontSize: 24, fontWeight: 'bold' }}>{selectedMetric?.label}</Text>
                            <TouchableOpacity onPress={() => setSelectedMetric(null)}>
                                <X color="#888" size={28} />
                            </TouchableOpacity>
                        </View>

                        {/* Time Range Filter */}
                        <View style={{ flexDirection: 'row', backgroundColor: '#111', borderRadius: 12, padding: 4, marginBottom: 20 }}>
                            {timeRangeOptions.map((option) => (
                                <TouchableOpacity
                                    key={option.value}
                                    onPress={() => handleTimeRangeChange(option.value)}
                                    style={{
                                        flex: 1,
                                        paddingVertical: 10,
                                        borderRadius: 8,
                                        backgroundColor: timeRange === option.value ? selectedMetric?.color || '#CCFF00' : 'transparent',
                                    }}
                                >
                                    <Text style={{
                                        textAlign: 'center',
                                        fontWeight: '600',
                                        fontSize: 13,
                                        color: timeRange === option.value ? '#050505' : '#888',
                                    }}>
                                        {option.label}
                                    </Text>
                                </TouchableOpacity>
                            ))}
                        </View>

                        {loadingHistory ? (
                            <Text style={{ color: '#888', textAlign: 'center', marginTop: 40 }}>Loading...</Text>
                        ) : (
                            <>
                                {/* Chart */}
                                {historyData.length > 0 && selectedMetric && (() => {
                                    // Filter out null values for proper charting
                                    const chartData = historyData
                                        .map((d, i) => ({ x: i, y: d[selectedMetric.key], date: d.date }))
                                        .filter(d => d.y !== null && d.y !== undefined);

                                    if (chartData.length === 0) return null;

                                    // Calculate domain with padding
                                    const values = chartData.map(d => d.y);
                                    const minVal = Math.min(...values);
                                    const maxVal = Math.max(...values);
                                    const padding = (maxVal - minVal) * 0.2 || 5; // 20% padding or 5 if no range

                                    return (
                                        <View style={{ marginBottom: 24 }}>
                                            {/* Selected Point Display */}
                                            {selectedPoint && (
                                                <View style={{ backgroundColor: selectedMetric.color + '20', borderRadius: 8, padding: 12, marginBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <Text style={{ color: '#888', fontSize: 13 }}>{selectedPoint.date}</Text>
                                                    <Text style={{ color: selectedMetric.color, fontSize: 18, fontWeight: 'bold' }}>
                                                        {selectedPoint.value} {selectedMetric.unit}
                                                    </Text>
                                                </View>
                                            )}
                                            <VictoryChart
                                                width={width - 48}
                                                height={200}
                                                padding={{ left: 50, right: 20, top: 20, bottom: 40 }}
                                                domain={{ y: [Math.max(0, minVal - padding), maxVal + padding] }}
                                                containerComponent={
                                                    <VictoryVoronoiContainer
                                                        onActivated={(points) => {
                                                            if (points && points.length > 0) {
                                                                const p = points[0];
                                                                setSelectedPoint({ date: p.date, value: p.y });
                                                            }
                                                        }}
                                                    />
                                                }
                                            >
                                                <VictoryLine
                                                    data={chartData}
                                                    style={{
                                                        data: { stroke: selectedMetric.color, strokeWidth: 3 }
                                                    }}
                                                    interpolation="monotoneX"
                                                />
                                                <VictoryScatter
                                                    data={chartData}
                                                    size={0}
                                                    style={{ data: { fill: selectedMetric.color } }}
                                                />
                                                <VictoryAxis
                                                    tickFormat={(t) => {
                                                        const dataPoint = chartData.find(d => d.x === Math.round(t));
                                                        if (dataPoint && chartData.indexOf(dataPoint) % 5 === 0) {
                                                            return dataPoint.date?.slice(5) || '';
                                                        }
                                                        return '';
                                                    }}
                                                    style={{
                                                        axis: { stroke: '#333' },
                                                        tickLabels: { fill: '#666', fontSize: 10 }
                                                    }}
                                                />
                                                <VictoryAxis
                                                    dependentAxis
                                                    style={{
                                                        axis: { stroke: '#333' },
                                                        tickLabels: { fill: '#666', fontSize: 10 }
                                                    }}
                                                />
                                            </VictoryChart>
                                        </View>
                                    );
                                })()}

                                {/* Statistics */}
                                {selectedMetric && (() => {
                                    const stats = getMetricStats(selectedMetric.key);
                                    const rangeLabel = timeRangeOptions.find(o => o.value === timeRange)?.label || '1M';
                                    return (
                                        <View style={{ backgroundColor: '#111', borderRadius: 16, padding: 16 }}>
                                            <Text style={{ color: '#666', fontSize: 12, marginBottom: 12, textTransform: 'uppercase' }}>{rangeLabel} Statistics</Text>

                                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 }}>
                                                <View style={{ alignItems: 'center', flex: 1 }}>
                                                    <Text style={{ color: '#888', fontSize: 11 }}>MIN</Text>
                                                    <Text style={{ color: 'white', fontSize: 20, fontWeight: 'bold' }}>{stats.min}</Text>
                                                </View>
                                                <View style={{ alignItems: 'center', flex: 1 }}>
                                                    <Text style={{ color: '#888', fontSize: 11 }}>AVG</Text>
                                                    <Text style={{ color: 'white', fontSize: 20, fontWeight: 'bold' }}>{stats.avg}</Text>
                                                </View>
                                                <View style={{ alignItems: 'center', flex: 1 }}>
                                                    <Text style={{ color: '#888', fontSize: 11 }}>MAX</Text>
                                                    <Text style={{ color: 'white', fontSize: 20, fontWeight: 'bold' }}>{stats.max}</Text>
                                                </View>
                                            </View>

                                            {/* Trend */}
                                            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingTop: 12, borderTopWidth: 1, borderTopColor: '#222' }}>
                                                {stats.trend > 0 ? (
                                                    <TrendingUp color="#00FF99" size={20} />
                                                ) : stats.trend < 0 ? (
                                                    <TrendingDown color="#FF3333" size={20} />
                                                ) : null}
                                                <Text style={{
                                                    color: stats.trend > 0 ? '#00FF99' : stats.trend < 0 ? '#FF3333' : '#888',
                                                    fontSize: 16,
                                                    fontWeight: 'bold',
                                                    marginLeft: 8
                                                }}>
                                                    {stats.trend > 0 ? '+' : ''}{stats.trend.toFixed(1)}% vs last week
                                                </Text>
                                            </View>
                                        </View>
                                    );
                                })()}
                            </>
                        )}
                    </View>
                </View>
            </Modal>

        </ScrollView>
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
        alignItems: 'center',
        marginBottom: 40,
        backgroundColor: '#111',
        padding: 20,
        borderRadius: 16,
    },
    avatar: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: '#CCFF00',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 16,
    },
    name: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
    },
    email: {
        color: '#888',
        fontSize: 14,
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
    card: {
        width: '48%',
        backgroundColor: '#1A1A1A',
        padding: 16,
        borderRadius: 12,
        gap: 12,
    },
    iconBox: {
        width: 40,
        height: 40,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    cardLabel: {
        color: '#888',
        fontSize: 12,
        marginBottom: 4,
    },
    cardValue: {
        color: 'white',
        fontSize: 20,
        fontWeight: 'bold',
    },
    cardUnit: {
        fontSize: 12,
        color: '#666',
        fontWeight: 'normal',
    },
    refreshButton: {
        backgroundColor: '#CCFF00',
        height: 56,
        borderRadius: 12,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 10,
        marginBottom: 12,
    },
    refreshButtonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
    },
    infoCard: {
        backgroundColor: '#111',
        borderRadius: 16,
        padding: 16,
        marginBottom: 20,
    },
    row: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 8,
    },
    label: {
        color: '#888',
        fontSize: 14,
    },
    value: {
        color: 'white',
        fontSize: 14,
        fontWeight: '600',
    },
    divider: {
        height: 1,
        backgroundColor: '#222',
        marginVertical: 8,
    },
    logoutButton: {
        backgroundColor: '#111',
        height: 56,
        borderRadius: 12,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 10,
    },
    logoutButtonText: {
        color: '#666',
        fontWeight: '600',
        fontSize: 16,
    },
});

export default ProfileScreen;
