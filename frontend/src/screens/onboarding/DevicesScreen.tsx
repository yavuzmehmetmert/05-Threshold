import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, FlatList } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useDashboardStore } from '../../store/useDashboardStore';
import { Watch, Activity, Zap, Plus, Check } from 'lucide-react-native';

const DEVICE_TYPES = [
    { type: 'Watch', icon: Watch, label: 'Garmin Watch', color: '#00CCFF' },
    { type: 'HRM', icon: Activity, label: 'Heart Rate Monitor', color: '#FF3333' },
    { type: 'Power', icon: Zap, label: 'Power Meter', color: '#CCFF00' },
];

const DevicesScreen = () => {
    const navigation = useNavigation<any>();
    const addDevice = useDashboardStore(state => state.addDevice);
    const devices = useDashboardStore(state => state.gear.devices);

    const handleAddDevice = (type: string, label: string) => {
        addDevice({ name: label, type });
    };

    return (
        <View style={styles.container}>
            <Text style={styles.header}>Hardware Arsenal</Text>
            <Text style={styles.subHeader}>Select the sensors you use. We aggregate data from all sources.</Text>

            <View style={styles.selectionArea}>
                {DEVICE_TYPES.map((device) => (
                    <TouchableOpacity
                        key={device.type}
                        style={styles.deviceOption}
                        onPress={() => handleAddDevice(device.type, device.label)}
                    >
                        <View style={[styles.iconBox, { backgroundColor: device.color + '20' }]}>
                            <device.icon color={device.color} size={24} />
                        </View>
                        <Text style={styles.deviceLabel}>{device.label}</Text>
                        <Plus color="#666" size={20} />
                    </TouchableOpacity>
                ))}
            </View>

            <Text style={styles.sectionTitle}>Connected Devices</Text>
            <FlatList
                data={devices}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                    <View style={styles.connectedDevice}>
                        <Text style={styles.connectedText}>{item.name}</Text>
                        <Check color="#CCFF00" size={16} />
                    </View>
                )}
                contentContainerStyle={styles.listContent}
                ListEmptyComponent={<Text style={styles.emptyText}>No devices added yet.</Text>}
            />

            <TouchableOpacity
                style={styles.button}
                onPress={() => navigation.navigate('Gear')}
            >
                <Text style={styles.buttonText}>Next: Shoe Rotation</Text>
            </TouchableOpacity>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        padding: 20,
        paddingTop: 60,
    },
    header: {
        fontSize: 32,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 10,
    },
    subHeader: {
        fontSize: 16,
        color: '#999',
        marginBottom: 40,
    },
    selectionArea: {
        gap: 12,
        marginBottom: 40,
    },
    deviceOption: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        padding: 16,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#222',
    },
    iconBox: {
        width: 40,
        height: 40,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 16,
    },
    deviceLabel: {
        flex: 1,
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
    },
    sectionTitle: {
        color: '#666',
        fontSize: 14,
        fontWeight: 'bold',
        marginBottom: 12,
        textTransform: 'uppercase',
        letterSpacing: 1,
    },
    listContent: {
        gap: 8,
    },
    connectedDevice: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#1A1A1A',
        padding: 12,
        borderRadius: 8,
    },
    connectedText: {
        color: '#ccc',
    },
    emptyText: {
        color: '#444',
        fontStyle: 'italic',
    },
    button: {
        backgroundColor: '#CCFF00',
        height: 56,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 20,
    },
    buttonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
    },
});

export default DevicesScreen;
