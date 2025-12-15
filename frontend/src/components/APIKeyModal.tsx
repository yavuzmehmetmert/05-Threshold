/**
 * API Key Settings Modal
 * Allows user to set their Gemini API key for AI Coach
 */
import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    Modal,
    StyleSheet,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { Settings, Key, X, Check, Trash2, Zap } from 'lucide-react-native';

const COLORS = {
    background: '#050505',
    surface: '#1A1A1A',
    surfaceLight: '#2A2A2A',
    primary: '#CCFF00',
    text: '#FFFFFF',
    textSecondary: '#888888',
    error: '#FF3333',
    success: '#00FF88',
};

interface APIKeyModalProps {
    visible: boolean;
    onClose: () => void;
}

export const APIKeyModal: React.FC<APIKeyModalProps> = ({ visible, onClose }) => {
    const [apiKey, setApiKey] = useState('');
    const [maskedKey, setMaskedKey] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);

    // Check if API key is set
    useEffect(() => {
        if (visible) {
            checkApiKey();
            setTestResult(null);
        }
    }, [visible]);

    const checkApiKey = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/coach/api-key');
            const data = await response.json();
            if (data.success && data.masked_key) {
                setMaskedKey(data.masked_key);
            } else {
                setMaskedKey(null);
            }
        } catch (error) {
            console.error('Failed to check API key:', error);
        } finally {
            setLoading(false);
        }
    };

    const saveApiKey = async () => {
        if (!apiKey || apiKey.length < 30) {
            Alert.alert('Hata', 'Geçerli bir API anahtarı girin');
            return;
        }

        setSaving(true);
        try {
            const response = await fetch('http://localhost:8000/coach/api-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey }),
            });
            const data = await response.json();

            if (data.success) {
                setMaskedKey(data.masked_key);
                setApiKey('');
                onClose(); // Close modal first
                Alert.alert('Başarılı ✅', 'API anahtarı kaydedildi!');
            } else {
                Alert.alert('Hata', data.message || 'Kayıt başarısız');
            }
        } catch (error) {
            Alert.alert('Hata', 'Bağlantı hatası');
        } finally {
            setSaving(false);
        }
    };

    const testApiKey = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const response = await fetch('http://localhost:8000/coach/api-key/test', {
                method: 'POST',
            });
            const data = await response.json();

            if (data.success) {
                setTestResult('success');
                Alert.alert('✅ Bağlantı Başarılı!', data.message || 'API anahtarı çalışıyor.');
            } else {
                setTestResult('error');
                Alert.alert('❌ Bağlantı Hatası', data.message || 'API anahtarı geçersiz veya bağlantı sorunu var.');
            }
        } catch (error) {
            setTestResult('error');
            Alert.alert('❌ Hata', 'Sunucuya bağlanılamadı');
        } finally {
            setTesting(false);
        }
    };

    const deleteApiKey = async () => {
        Alert.alert(
            'API Anahtarını Sil',
            'API anahtarınızı silmek istediğinize emin misiniz?',
            [
                { text: 'İptal', style: 'cancel' },
                {
                    text: 'Sil',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            await fetch('http://localhost:8000/coach/api-key', {
                                method: 'DELETE',
                            });
                            setMaskedKey(null);
                            setApiKey('');
                            setTestResult(null);
                        } catch (error) {
                            Alert.alert('Hata', 'Silme başarısız');
                        }
                    },
                },
            ]
        );
    };

    return (
        <Modal
            visible={visible}
            transparent
            animationType="fade"
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <View style={styles.modal}>
                    {/* Header */}
                    <View style={styles.header}>
                        <View style={styles.headerTitle}>
                            <Key size={20} color={COLORS.primary} />
                            <Text style={styles.title}>Gemini API Anahtarı</Text>
                        </View>
                        <TouchableOpacity onPress={onClose}>
                            <X size={24} color={COLORS.textSecondary} />
                        </TouchableOpacity>
                    </View>

                    {/* Content */}
                    {loading ? (
                        <ActivityIndicator color={COLORS.primary} style={styles.loader} />
                    ) : (
                        <>
                            {/* Current Key Status */}
                            {maskedKey && (
                                <View style={styles.currentKey}>
                                    <Text style={styles.label}>Mevcut Anahtar</Text>
                                    <View style={styles.keyRow}>
                                        <Text style={[
                                            styles.maskedKey,
                                            testResult === 'success' && { color: COLORS.success },
                                            testResult === 'error' && { color: COLORS.error },
                                        ]}>{maskedKey}</Text>
                                        <View style={{ flexDirection: 'row', gap: 12 }}>
                                            <TouchableOpacity onPress={testApiKey} disabled={testing}>
                                                {testing ? (
                                                    <ActivityIndicator size={18} color={COLORS.primary} />
                                                ) : (
                                                    <Zap size={18} color={COLORS.primary} />
                                                )}
                                            </TouchableOpacity>
                                            <TouchableOpacity onPress={deleteApiKey}>
                                                <Trash2 size={18} color={COLORS.error} />
                                            </TouchableOpacity>
                                        </View>
                                    </View>
                                    {testResult === 'success' && (
                                        <Text style={styles.testSuccess}>✓ Bağlantı başarılı</Text>
                                    )}
                                    {testResult === 'error' && (
                                        <Text style={styles.testError}>✗ Bağlantı hatası</Text>
                                    )}
                                </View>
                            )}

                            {/* Input */}
                            <View style={styles.inputContainer}>
                                <Text style={styles.label}>
                                    {maskedKey ? 'Yeni Anahtar' : 'API Anahtarı'}
                                </Text>
                                <TextInput
                                    style={styles.input}
                                    placeholder="AIza..."
                                    placeholderTextColor={COLORS.textSecondary}
                                    value={apiKey}
                                    onChangeText={setApiKey}
                                    secureTextEntry
                                    autoCapitalize="none"
                                    autoCorrect={false}
                                />
                            </View>

                            {/* Help Text */}
                            <Text style={styles.helpText}>
                                Gemini API anahtarını Google AI Studio'dan alabilirsin:{'\n'}
                                https://aistudio.google.com/app/apikey
                            </Text>

                            {/* Buttons */}
                            <View style={styles.buttonRow}>
                                {/* Test Button - only show if key exists */}
                                {maskedKey && (
                                    <TouchableOpacity
                                        style={[styles.testButton, testing && styles.buttonDisabled]}
                                        onPress={testApiKey}
                                        disabled={testing}
                                    >
                                        {testing ? (
                                            <ActivityIndicator color={COLORS.primary} size="small" />
                                        ) : (
                                            <>
                                                <Zap size={16} color={COLORS.primary} />
                                                <Text style={styles.testButtonText}>Test Et</Text>
                                            </>
                                        )}
                                    </TouchableOpacity>
                                )}

                                {/* Save Button */}
                                <TouchableOpacity
                                    style={[
                                        styles.saveButton,
                                        saving && styles.buttonDisabled,
                                        !maskedKey && { flex: 1 }
                                    ]}
                                    onPress={saveApiKey}
                                    disabled={saving}
                                >
                                    {saving ? (
                                        <ActivityIndicator color={COLORS.background} size="small" />
                                    ) : (
                                        <>
                                            <Check size={18} color={COLORS.background} />
                                            <Text style={styles.saveButtonText}>Kaydet</Text>
                                        </>
                                    )}
                                </TouchableOpacity>
                            </View>
                        </>
                    )}
                </View>
            </View>
        </Modal>
    );
};

// Settings Button Component
interface SettingsButtonProps {
    onPress: () => void;
}

export const SettingsButton: React.FC<SettingsButtonProps> = ({ onPress }) => (
    <TouchableOpacity style={styles.settingsButton} onPress={onPress}>
        <Settings size={20} color={COLORS.primary} />
    </TouchableOpacity>
);

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    modal: {
        backgroundColor: COLORS.surface,
        borderRadius: 16,
        padding: 20,
        width: '90%',
        maxWidth: 400,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
    },
    headerTitle: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    title: {
        color: COLORS.text,
        fontSize: 18,
        fontWeight: '600',
    },
    loader: {
        marginVertical: 40,
    },
    currentKey: {
        marginBottom: 16,
    },
    label: {
        color: COLORS.textSecondary,
        fontSize: 13,
        marginBottom: 6,
    },
    keyRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: COLORS.surfaceLight,
        padding: 12,
        borderRadius: 8,
    },
    maskedKey: {
        color: COLORS.success,
        fontFamily: 'monospace',
        fontSize: 14,
    },
    inputContainer: {
        marginBottom: 16,
    },
    input: {
        backgroundColor: COLORS.surfaceLight,
        borderRadius: 8,
        padding: 12,
        color: COLORS.text,
        fontSize: 14,
        fontFamily: 'monospace',
    },
    helpText: {
        color: COLORS.textSecondary,
        fontSize: 12,
        marginBottom: 20,
        lineHeight: 18,
    },
    buttonRow: {
        flexDirection: 'row',
        gap: 10,
    },
    testButton: {
        flex: 1,
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderColor: COLORS.primary,
        borderRadius: 8,
        padding: 14,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 6,
    },
    testButtonText: {
        color: COLORS.primary,
        fontSize: 15,
        fontWeight: '600',
    },
    saveButton: {
        flex: 1,
        backgroundColor: COLORS.primary,
        borderRadius: 8,
        padding: 14,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 6,
    },
    buttonDisabled: {
        opacity: 0.6,
    },
    saveButtonText: {
        color: COLORS.background,
        fontSize: 15,
        fontWeight: '600',
    },
    testSuccess: {
        color: COLORS.success,
        fontSize: 12,
        marginTop: 6,
    },
    testError: {
        color: COLORS.error,
        fontSize: 12,
        marginTop: 6,
    },
    settingsButton: {
        padding: 8,
    },
});

export default APIKeyModal;
