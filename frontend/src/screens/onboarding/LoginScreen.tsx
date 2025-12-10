import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Lock, Mail, CheckCircle } from 'lucide-react-native';

const LoginScreen = () => {
    const navigation = useNavigation<any>();
    const [email, setEmail] = useState('yavuzmehmetmert@gmail.com'); // Pre-filled for dev
    const [password, setPassword] = useState('gucfax-1denfY-pemqin'); // Pre-filled for dev
    const [loading, setLoading] = useState(false);

    const handleLogin = async () => {
        setLoading(true);
        try {
            // Simulate API call to backend check
            const response = await fetch('http://localhost:8000/auth/login-check');
            if (response.ok) {
                // Success
                setTimeout(() => {
                    setLoading(false);
                    navigation.navigate('Sync');
                }, 1500);
            } else {
                throw new Error('Connection failed');
            }
        } catch (error) {
            setLoading(false);
            Alert.alert('Login Failed', 'Could not connect to Garmin services. Please check backend.');
            // For demo purposes, allow proceeding even if backend fails locally if user insists (optional)
            navigation.navigate('Sync'); // UNCOMMENT FOR DEV IF BACKEND IS DOWN
        }
    };

    return (
        <View style={styles.container}>
            <Text style={styles.header}>Connect Garmin</Text>
            <Text style={styles.subHeader}>Sync your history to build your profile.</Text>

            <View style={styles.form}>
                <View style={styles.inputContainer}>
                    <Mail color="#666" size={20} />
                    <TextInput
                        style={styles.input}
                        placeholder="Email"
                        placeholderTextColor="#666"
                        value={email}
                        onChangeText={setEmail}
                        autoCapitalize="none"
                    />
                </View>

                <View style={styles.inputContainer}>
                    <Lock color="#666" size={20} />
                    <TextInput
                        style={styles.input}
                        placeholder="Password"
                        placeholderTextColor="#666"
                        value={password}
                        onChangeText={setPassword}
                        secureTextEntry
                    />
                </View>

                <TouchableOpacity
                    style={styles.button}
                    onPress={handleLogin}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator color="#050505" />
                    ) : (
                        <Text style={styles.buttonText}>Connect & Sync</Text>
                    )}
                </TouchableOpacity>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        padding: 20,
        justifyContent: 'center',
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
        gap: 20,
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
    button: {
        backgroundColor: '#00CCFF', // Garmin Blue-ish
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

export default LoginScreen;
