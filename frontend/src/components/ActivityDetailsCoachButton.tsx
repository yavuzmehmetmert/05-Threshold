import React, { useState } from 'react';
import { TouchableOpacity, View, Text, TextInput, StyleSheet, ActivityIndicator } from 'react-native';
import { MessageCircle, Send, X } from 'lucide-react-native';

const API_BASE = 'http://localhost:8000';

interface Props {
    garminActivityId: number;
    userId: number;
}

/**
 * ActivityDetailsCoachButton
 * 
 * A button that appears on activity detail pages.
 * Opens a mini chat interface to ask questions about that specific activity.
 */
export const ActivityDetailsCoachButton: React.FC<Props> = ({ garminActivityId, userId }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [message, setMessage] = useState('');
    const [response, setResponse] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const sendMessage = async () => {
        if (!message.trim()) return;

        setLoading(true);
        setError('');
        setResponse('');

        try {
            const res = await fetch(`${API_BASE}/api/coach/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    message: message,
                    garmin_activity_id: garminActivityId,
                    deep_analysis_mode: false,
                    debug: false
                })
            });

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            const data = await res.json();
            setResponse(data.message);
        } catch (e: any) {
            setError(e.message || 'Failed to get response');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <TouchableOpacity
                style={styles.floatingButton}
                onPress={() => setIsOpen(true)}
            >
                <MessageCircle size={24} color="#fff" />
                <Text style={styles.buttonText}>Hoca'ya Sor</Text>
            </TouchableOpacity>
        );
    }

    return (
        <View style={styles.chatPanel}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>🏃 Hoca</Text>
                <TouchableOpacity onPress={() => setIsOpen(false)}>
                    <X size={24} color="#666" />
                </TouchableOpacity>
            </View>

            {response ? (
                <View style={styles.responseBox}>
                    <Text style={styles.responseText}>{response}</Text>
                </View>
            ) : null}

            {error ? (
                <Text style={styles.errorText}>{error}</Text>
            ) : null}

            <View style={styles.inputRow}>
                <TextInput
                    style={styles.input}
                    value={message}
                    onChangeText={setMessage}
                    placeholder="Bu antrenman hakkında bir soru sor..."
                    placeholderTextColor="#999"
                    editable={!loading}
                />
                <TouchableOpacity
                    style={[styles.sendButton, loading && styles.sendButtonDisabled]}
                    onPress={sendMessage}
                    disabled={loading}
                >
                    {loading ? (
                        <ActivityIndicator size="small" color="#fff" />
                    ) : (
                        <Send size={20} color="#fff" />
                    )}
                </TouchableOpacity>
            </View>

            <View style={styles.suggestions}>
                <TouchableOpacity
                    style={styles.suggestionChip}
                    onPress={() => setMessage('Bu antrenmanın interval yapısını anlat')}
                >
                    <Text style={styles.suggestionText}>Interval yapısı</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={styles.suggestionChip}
                    onPress={() => setMessage('Nabız bölgelerimi değerlendir')}
                >
                    <Text style={styles.suggestionText}>Nabız bölgeleri</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    floatingButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#4CAF50',
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderRadius: 24,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.25,
        shadowRadius: 4,
        elevation: 5,
    },
    buttonText: {
        color: '#fff',
        fontWeight: '600',
        marginLeft: 8,
        fontSize: 14,
    },
    chatPanel: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 8,
        maxWidth: 400,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
        paddingBottom: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '700',
    },
    responseBox: {
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
    },
    responseText: {
        fontSize: 14,
        lineHeight: 20,
        color: '#333',
    },
    errorText: {
        color: '#d32f2f',
        fontSize: 12,
        marginBottom: 8,
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    input: {
        flex: 1,
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 8,
        paddingHorizontal: 12,
        paddingVertical: 10,
        fontSize: 14,
    },
    sendButton: {
        backgroundColor: '#4CAF50',
        padding: 10,
        borderRadius: 8,
    },
    sendButtonDisabled: {
        backgroundColor: '#ccc',
    },
    suggestions: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
        marginTop: 12,
    },
    suggestionChip: {
        backgroundColor: '#e8f5e9',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
    },
    suggestionText: {
        color: '#2e7d32',
        fontSize: 12,
    },
});

export default ActivityDetailsCoachButton;
