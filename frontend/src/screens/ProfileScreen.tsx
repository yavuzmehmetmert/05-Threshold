import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, RefreshControl, Modal, TextInput, Alert } from 'react-native';
import { useDashboardStore } from '../store/useDashboardStore';
import { User, RefreshCw, Activity, Heart, Scale, Wind, LogOut, Plus, Trash2 } from 'lucide-react-native';

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

    // Shoes State
    const [shoes, setShoes] = useState<ShoeData[]>([]);
    const [showAddShoe, setShowAddShoe] = useState(false);
    const [newShoeName, setNewShoeName] = useState('');
    const [newShoeBrand, setNewShoeBrand] = useState('');
    const [newShoeInitialKm, setNewShoeInitialKm] = useState('0');

    useEffect(() => {
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
            const response = await fetch('http://localhost:8000/ingestion/profile');
            if (response.ok) {
                const realData = await response.json();
                setDebugData(realData);
                updateUserProfile({
                    maxHr: realData.maxHr,
                    restingHr: realData.restingHr,
                    lthr: realData.lthr,
                    weight: realData.weight,
                    name: realData.name,
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
                <Text style={styles.sectionTitle}>Physiological Profile</Text>
                <View style={styles.grid}>
                    <MetricCard icon={Scale} label="Weight" value={userProfile.weight} unit="kg" color="#CCFF00" />
                    <MetricCard icon={Heart} label="Resting HR" value={userProfile.restingHr} unit="bpm" color="#00CCFF" />
                    <MetricCard icon={Activity} label="Lactate Threshold" value={userProfile.lthr} unit="bpm" color="#FF3333" />
                    <MetricCard icon={Wind} label="VO2 Max" value={userProfile.vo2max} unit="ml/kg/min" color="#CC00FF" />
                    <MetricCard icon={Heart} label="Max HR" value={userProfile.maxHr} unit="bpm" color="#FF9900" />
                    <MetricCard icon={Activity} label="Stress Score" value={userProfile.stressScore || '-'} unit="/100" color={userProfile.stressScore > 50 ? "#FF3333" : "#00FF99"} />
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
