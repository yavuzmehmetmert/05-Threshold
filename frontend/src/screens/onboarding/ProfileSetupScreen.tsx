import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useDashboardStore } from '../../store/useDashboardStore';
import { Heart, Scale, Activity } from 'lucide-react-native';

const ProfileSetupScreen = () => {
    const navigation = useNavigation<any>();
    const updateUserProfile = useDashboardStore(state => state.updateUserProfile);
    const userProfile = useDashboardStore(state => state.userProfile);

    const [maxHr, setMaxHr] = useState(userProfile.maxHr.toString());
    const [restingHr, setRestingHr] = useState(userProfile.restingHr.toString());
    const [lthr, setLthr] = useState(userProfile.lthr.toString());
    const [weight, setWeight] = useState(userProfile.weight.toString());

    const handleNext = () => {
        updateUserProfile({
            maxHr: parseInt(maxHr),
            restingHr: parseInt(restingHr),
            lthr: parseInt(lthr),
            weight: parseInt(weight),
        });
        navigation.navigate('Devices');
    };

    return (
        <ScrollView contentContainerStyle={styles.container}>
            <Text style={styles.header}>Physiology</Text>
            <Text style={styles.subHeader}>Confirm your biological baselines. These are critical for accurate training zones.</Text>

            <View style={styles.form}>
                <View style={styles.inputGroup}>
                    <Text style={styles.label}>Max Heart Rate</Text>
                    <View style={styles.inputContainer}>
                        <Heart color="#FF3333" size={20} />
                        <TextInput
                            style={styles.input}
                            value={maxHr}
                            onChangeText={setMaxHr}
                            keyboardType="numeric"
                        />
                        <Text style={styles.unit}>bpm</Text>
                    </View>
                </View>

                <View style={styles.inputGroup}>
                    <Text style={styles.label}>Resting Heart Rate</Text>
                    <View style={styles.inputContainer}>
                        <Activity color="#00CCFF" size={20} />
                        <TextInput
                            style={styles.input}
                            value={restingHr}
                            onChangeText={setRestingHr}
                            keyboardType="numeric"
                        />
                        <Text style={styles.unit}>bpm</Text>
                    </View>
                </View>

                <View style={styles.inputGroup}>
                    <Text style={styles.label}>Lactate Threshold (LTHR)</Text>
                    <View style={styles.inputContainer}>
                        <Activity color="#CCFF00" size={20} />
                        <TextInput
                            style={styles.input}
                            value={lthr}
                            onChangeText={setLthr}
                            keyboardType="numeric"
                        />
                        <Text style={styles.unit}>bpm</Text>
                    </View>
                </View>

                <View style={styles.inputGroup}>
                    <Text style={styles.label}>Weight</Text>
                    <View style={styles.inputContainer}>
                        <Scale color="#999" size={20} />
                        <TextInput
                            style={styles.input}
                            value={weight}
                            onChangeText={setWeight}
                            keyboardType="numeric"
                        />
                        <Text style={styles.unit}>kg</Text>
                    </View>
                </View>

                <TouchableOpacity style={styles.button} onPress={handleNext}>
                    <Text style={styles.buttonText}>Next: Devices</Text>
                </TouchableOpacity>
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
    form: {
        gap: 24,
    },
    inputGroup: {
        gap: 8,
    },
    label: {
        color: '#ccc',
        fontSize: 14,
        fontWeight: '600',
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
        fontSize: 18,
        fontWeight: 'bold',
    },
    unit: {
        color: '#666',
        fontSize: 14,
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

export default ProfileSetupScreen;
