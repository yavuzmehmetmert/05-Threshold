import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { RefreshCw, Check } from 'lucide-react-native';
import { useDashboardStore } from '../../store/useDashboardStore';

const SyncScreen = () => {
    const navigation = useNavigation<any>();
    const updateUserProfile = useDashboardStore(state => state.updateUserProfile);
    const [status, setStatus] = useState('Connecting to Garmin...');
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        // Simulate sync process
        const steps = [
            { msg: 'Authenticating...', time: 1000 },
            { msg: 'Fetching User Profile...', time: 2000 },
            { msg: 'Downloading Activities (Last 90 Days)...', time: 3500 },
            { msg: 'Calculating Thresholds...', time: 5000 },
            { msg: 'Sync Complete!', time: 6000 },
        ];

        let currentStep = 0;

        const interval = setInterval(() => {
            if (currentStep < steps.length) {
                setStatus(steps[currentStep].msg);
                setProgress((currentStep + 1) / steps.length);
                currentStep++;
            } else {
                clearInterval(interval);

                // FETCH REAL DATA FROM BACKEND
                console.log('Fetching profile from backend...');
                fetch('http://localhost:8000/ingestion/profile')
                    .then(res => res.json())
                    .then(realData => {
                        console.log('Received Profile Data:', realData);
                        updateUserProfile({
                            maxHr: realData.maxHr || 190,
                            restingHr: realData.restingHr || 50,
                            lthr: realData.lthr || 170,
                            weight: realData.weight || 70,
                            vo2max: realData.vo2max || 50,
                            stressScore: realData.stressScore || 25,
                            name: realData.name || 'Runner'
                        });
                    })
                    .catch(err => console.error('Sync Error:', err))
                    .finally(() => {
                        setTimeout(() => navigation.navigate('ProfileSetup'), 1000);
                    });
            }
        }, 1200);

        return () => clearInterval(interval);
    }, []);

    return (
        <View style={styles.container}>
            <View style={styles.iconContainer}>
                {progress < 1 ? (
                    <RefreshCw color="#CCFF00" size={48} style={{ opacity: 0.8 }} />
                ) : (
                    <Check color="#CCFF00" size={48} />
                )}
            </View>

            <Text style={styles.status}>{status}</Text>

            <View style={styles.progressBarBg}>
                <View style={[styles.progressBarFill, { width: `${progress * 100}%` }]} />
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 40,
    },
    iconContainer: {
        marginBottom: 40,
    },
    status: {
        color: 'white',
        fontSize: 18,
        fontWeight: '600',
        marginBottom: 20,
        textAlign: 'center',
    },
    progressBarBg: {
        width: '100%',
        height: 6,
        backgroundColor: '#333',
        borderRadius: 3,
        overflow: 'hidden',
    },
    progressBarFill: {
        height: '100%',
        backgroundColor: '#CCFF00',
    },
});

export default SyncScreen;
