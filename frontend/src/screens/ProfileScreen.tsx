import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, RefreshControl } from 'react-native';
import { useDashboardStore } from '../store/useDashboardStore';
import { User, RefreshCw, Activity, Heart, Scale, Wind, LogOut } from 'lucide-react-native';

const MetricCard = ({ icon: Icon, label, value, unit, color }: any) => (
    <View style={styles.card}>
        <View style={[styles.iconBox, { backgroundColor: color + '20' }]}>
            <Icon color={color} size={24} />
        </View>
        <View>
            <Text style={styles.cardLabel}>{label}</Text>
            <Text style={styles.cardValue}>{value} <Text style={styles.cardUnit}>{unit}</Text></Text>
        </View>
    </View>
);

const ProfileScreen = () => {
    const userProfile = useDashboardStore(state => state.userProfile);
    const goals = useDashboardStore(state => state.goals);
    const updateUserProfile = useDashboardStore(state => state.updateUserProfile);
    const [refreshing, setRefreshing] = useState(false);
    const [debugData, setDebugData] = useState<any>(null);

    const onRefresh = async () => {
        setRefreshing(true);
        try {
            const response = await fetch('http://localhost:8000/ingestion/profile');
            if (response.ok) {
                const realData = await response.json();
                setDebugData(realData); // Store raw data for debugging
                updateUserProfile({
                    maxHr: realData.maxHr,
                    restingHr: realData.restingHr,
                    lthr: realData.lthr,
                    weight: realData.weight,
                    name: realData.name,
                    vo2max: realData.vo2max,
                    stressScore: realData.stressScore,
                    // email: realData.email // Backend doesn't send email yet, need to fix
                });
            }
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
                <Text style={styles.sectionTitle}>Physiological Profile</Text>
                <View style={styles.grid}>
                    <MetricCard
                        icon={Scale}
                        label="Weight"
                        value={userProfile.weight}
                        unit="kg"
                        color="#CCFF00"
                    />
                    <MetricCard
                        icon={Heart}
                        label="Resting HR"
                        value={userProfile.restingHr}
                        unit="bpm"
                        color="#00CCFF"
                    />
                    <MetricCard
                        icon={Activity}
                        label="Lactate Threshold"
                        value={userProfile.lthr}
                        unit="bpm"
                        color="#FF3333"
                    />
                    <MetricCard
                        icon={Wind}
                        label="VO2 Max"
                        value={userProfile.vo2max}
                        unit="ml/kg/min"
                        color="#CC00FF"
                    />
                    <MetricCard
                        icon={Heart}
                        label="Max HR"
                        value={userProfile.maxHr}
                        unit="bpm"
                        color="#FF9900"
                    />
                    <MetricCard
                        icon={Activity}
                        label="Stress Score"
                        value={userProfile.stressScore || '-'}
                        unit="/100"
                        color={userProfile.stressScore > 50 ? "#FF3333" : "#00FF99"}
                    />
                </View>
            </View>

            {/* Training Context Section */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Training Schedule</Text>
                <View style={styles.card}>
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

            <View style={{ marginTop: 20, padding: 10, backgroundColor: '#111', borderRadius: 8 }}>
                <Text style={{ color: '#CCFF00', marginBottom: 5, fontWeight: 'bold' }}>DEBUG API RESPONSE:</Text>
                <Text style={{ color: '#888', fontFamily: 'monospace', fontSize: 10 }}>
                    {JSON.stringify(debugData, null, 2)}
                </Text>
            </View>

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
    card: {
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
