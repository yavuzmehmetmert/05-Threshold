import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, FlatList } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useDashboardStore } from '../../store/useDashboardStore';
import { Footprints, Plus, Trash2 } from 'lucide-react-native';

const GearScreen = () => {
    const navigation = useNavigation<any>();
    const addShoe = useDashboardStore(state => state.addShoe);
    const shoes = useDashboardStore(state => state.gear.shoes);

    const [shoeName, setShoeName] = useState('');
    const [mileage, setMileage] = useState('');

    const handleAddShoe = () => {
        if (shoeName) {
            addShoe({ name: shoeName, mileage: parseInt(mileage) || 0 });
            setShoeName('');
            setMileage('');
        }
    };

    const handleNext = () => {
        navigation.navigate('Context');
    };

    return (
        <View style={styles.container}>
            <Text style={styles.header}>Shoe Rotation</Text>
            <Text style={styles.subHeader}>Add your active rotation. We'll track mileage to prevent injury.</Text>

            <View style={styles.inputArea}>
                <View style={styles.row}>
                    <View style={[styles.inputContainer, { flex: 2 }]}>
                        <Footprints color="#CCFF00" size={20} />
                        <TextInput
                            style={styles.input}
                            value={shoeName}
                            onChangeText={setShoeName}
                            placeholder="Model Name"
                            placeholderTextColor="#666"
                        />
                    </View>
                    <View style={[styles.inputContainer, { flex: 1 }]}>
                        <TextInput
                            style={styles.input}
                            value={mileage}
                            onChangeText={setMileage}
                            placeholder="0"
                            placeholderTextColor="#666"
                            keyboardType="numeric"
                        />
                        <Text style={styles.unit}>km</Text>
                    </View>
                </View>

                <TouchableOpacity style={styles.addButton} onPress={handleAddShoe}>
                    <Plus color="#050505" size={24} />
                    <Text style={styles.addButtonText}>Add Shoe</Text>
                </TouchableOpacity>
            </View>

            <Text style={styles.sectionTitle}>Your Rotation</Text>
            <FlatList
                data={shoes}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                    <View style={styles.shoeItem}>
                        <Text style={styles.shoeName}>{item.name}</Text>
                        <Text style={styles.shoeMileage}>{item.mileage} km</Text>
                    </View>
                )}
                contentContainerStyle={styles.listContent}
                ListEmptyComponent={<Text style={styles.emptyText}>No shoes added yet.</Text>}
            />

            <TouchableOpacity style={styles.button} onPress={handleNext}>
                <Text style={styles.buttonText}>Next: Meet Your Coach</Text>
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
        marginBottom: 30,
    },
    inputArea: {
        gap: 12,
        marginBottom: 30,
    },
    row: {
        flexDirection: 'row',
        gap: 10,
    },
    inputContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        borderWidth: 1,
        borderColor: '#333',
        borderRadius: 12,
        paddingHorizontal: 16,
        height: 56,
        gap: 12,
    },
    input: {
        flex: 1,
        color: 'white',
        fontSize: 16,
    },
    unit: {
        color: '#666',
        fontSize: 14,
    },
    addButton: {
        backgroundColor: '#CCFF00',
        height: 48,
        borderRadius: 12,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 8,
    },
    addButtonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
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
    shoeItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#1A1A1A',
        padding: 16,
        borderRadius: 8,
    },
    shoeName: {
        color: 'white',
        fontWeight: '600',
        fontSize: 16,
    },
    shoeMileage: {
        color: '#888',
    },
    emptyText: {
        color: '#444',
        fontStyle: 'italic',
    },
    button: {
        backgroundColor: '#00CCFF',
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

export default GearScreen;
