import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useDashboardStore } from '../../store/useDashboardStore';
import { Brain, ArrowRight } from 'lucide-react-native';

const GoalsScreen = () => {
    const navigation = useNavigation<any>();
    const setOnboarded = useDashboardStore(state => state.setOnboarded);

    const handleFinish = () => {
        setOnboarded(true);
    };

    return (
        <View style={styles.container}>
            <View style={styles.iconContainer}>
                <Brain color="#CCFF00" size={64} />
            </View>

            <Text style={styles.header}>Analysis Complete</Text>

            <Text style={styles.description}>
                I have processed your physiological history.
            </Text>

            <View style={styles.card}>
                <Text style={styles.cardText}>
                    "Your aerobic base is strong, but your lactate threshold power has plateaued. We need to focus on VO2max intervals this block."
                </Text>
                <Text style={styles.cardFooter}>- Threshold AI</Text>
            </View>

            <Text style={styles.subDescription}>
                We will define your season goals together in our first strategy session. I need to understand your context—sleep, stress, and life load—before we build the plan.
            </Text>

            <View style={{ flex: 1 }} />

            <TouchableOpacity style={styles.button} onPress={handleFinish}>
                <Text style={styles.buttonText}>Enter Dashboard</Text>
                <ArrowRight color="#050505" size={20} />
            </TouchableOpacity>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        padding: 30,
        paddingTop: 80,
        alignItems: 'center',
    },
    iconContainer: {
        marginBottom: 30,
        shadowColor: '#CCFF00',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.5,
        shadowRadius: 20,
    },
    header: {
        fontSize: 32,
        fontWeight: '900',
        color: 'white',
        marginBottom: 16,
        textAlign: 'center',
    },
    description: {
        fontSize: 18,
        color: '#ccc',
        textAlign: 'center',
        marginBottom: 40,
    },
    card: {
        backgroundColor: '#111',
        padding: 24,
        borderRadius: 16,
        borderLeftWidth: 4,
        borderLeftColor: '#CCFF00',
        marginBottom: 40,
        width: '100%',
    },
    cardText: {
        color: 'white',
        fontSize: 16,
        fontStyle: 'italic',
        lineHeight: 24,
        marginBottom: 12,
    },
    cardFooter: {
        color: '#CCFF00',
        fontWeight: 'bold',
        textAlign: 'right',
    },
    subDescription: {
        fontSize: 14,
        color: '#888',
        textAlign: 'center',
        lineHeight: 22,
        maxWidth: 300,
    },
    button: {
        backgroundColor: '#CCFF00',
        width: '100%',
        height: 56,
        borderRadius: 30,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 10,
    },
    buttonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
    },
});

export default GoalsScreen;
