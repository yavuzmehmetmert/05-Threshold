import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ImageBackground } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ArrowRight } from 'lucide-react-native';

const WelcomeScreen = () => {
    const navigation = useNavigation<any>();

    return (
        <View style={styles.container}>
            <View style={styles.content}>
                <Text style={styles.title}>THRESHOLD</Text>
                <Text style={styles.subtitle}>Your Adaptive AI Coach</Text>

                <View style={styles.spacer} />

                <Text style={styles.description}>
                    Train smarter, not harder. Threshold analyzes your biology and performance to prescribe the perfect workout, every day.
                </Text>

                <TouchableOpacity
                    style={styles.button}
                    onPress={() => navigation.navigate('Login')}
                >
                    <Text style={styles.buttonText}>Get Started</Text>
                    <ArrowRight color="#050505" size={20} />
                </TouchableOpacity>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        justifyContent: 'center',
        padding: 20,
    },
    content: {
        alignItems: 'center',
        gap: 10,
    },
    title: {
        fontSize: 42,
        fontWeight: '900',
        color: 'white',
        letterSpacing: 2,
    },
    subtitle: {
        fontSize: 18,
        color: '#CCFF00',
        fontWeight: '600',
        letterSpacing: 1,
    },
    spacer: {
        height: 40,
    },
    description: {
        color: '#999',
        textAlign: 'center',
        fontSize: 16,
        lineHeight: 24,
        marginBottom: 40,
        maxWidth: 300,
    },
    button: {
        backgroundColor: '#CCFF00',
        paddingVertical: 16,
        paddingHorizontal: 32,
        borderRadius: 30,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    buttonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
    },
});

export default WelcomeScreen;
