/**
 * Hoca Chat Modal
 * AI Running Coach Chat Interface
 */
import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    Modal,
    StyleSheet,
    ScrollView,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
} from 'react-native';
import { MessageCircle, X, Send, Bot, User, Sparkles } from 'lucide-react-native';

const COLORS = {
    background: '#050505',
    surface: '#1A1A1A',
    surfaceLight: '#2A2A2A',
    primary: '#CCFF00',
    text: '#FFFFFF',
    textSecondary: '#888888',
    error: '#FF3333',
};

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

interface HocaChatModalProps {
    visible: boolean;
    onClose: () => void;
    activityId?: number; // If opened from activity detail
    initialMessage?: string;
}

export const HocaChatModal: React.FC<HocaChatModalProps> = ({
    visible,
    onClose,
    activityId,
    initialMessage,
}) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const scrollViewRef = useRef<ScrollView>(null);

    // Reset on open
    useEffect(() => {
        if (visible) {
            if (initialMessage) {
                setInputText(initialMessage);
            }
            // Could load conversation history on open
        }
    }, [visible, initialMessage]);

    const sendMessage = async (text?: string) => {
        const messageText = text || inputText.trim();
        if (!messageText) return;

        // Add user message
        const userMessage: Message = {
            role: 'user',
            content: messageText,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMessage]);
        setInputText('');
        setLoading(true);
        setSuggestions([]);

        try {
            const response = await fetch('http://localhost:8000/coach/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: messageText,
                    activity_id: activityId,
                    mode: 'chat',
                    debug_metadata: false,
                }),
            });

            const data = await response.json();

            // Add assistant message
            const assistantMessage: Message = {
                role: 'assistant',
                content: data.message || 'Bir hata oluştu.',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, assistantMessage]);

            // Set suggestions if available
            if (data.suggestions && data.suggestions.length > 0) {
                setSuggestions(data.suggestions);
            }
        } catch (error) {
            const errorMessage: Message = {
                role: 'assistant',
                content: '⚠️ Bağlantı hatası. Lütfen API anahtarınızı kontrol edin.',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    const scrollToBottom = () => {
        setTimeout(() => {
            scrollViewRef.current?.scrollToEnd({ animated: true });
        }, 100);
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    return (
        <Modal
            visible={visible}
            animationType="slide"
            presentationStyle="pageSheet"
            onRequestClose={onClose}
        >
            <KeyboardAvoidingView
                style={styles.container}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            >
                {/* Header */}
                <View style={styles.header}>
                    <View style={styles.headerTitle}>
                        <View style={styles.avatar}>
                            <Bot size={24} color={COLORS.background} />
                        </View>
                        <View>
                            <Text style={styles.title}>Hoca</Text>
                            <Text style={styles.subtitle}>AI Koşu Koçu</Text>
                        </View>
                    </View>
                    <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                        <X size={24} color={COLORS.text} />
                    </TouchableOpacity>
                </View>

                {/* Messages */}
                <ScrollView
                    ref={scrollViewRef}
                    style={styles.messagesContainer}
                    contentContainerStyle={styles.messagesContent}
                >
                    {messages.length === 0 && (
                        <View style={styles.emptyState}>
                            <Sparkles size={48} color={COLORS.primary} />
                            <Text style={styles.emptyTitle}>Merhaba! 👋</Text>
                            <Text style={styles.emptyText}>
                                Ben Hoca, senin AI koşu koçunum.{'\n'}
                                Antrenmanların, hedeflerin veya koşuyla ilgili{'\n'}
                                her konuda sana yardımcı olabilirim.
                            </Text>
                        </View>
                    )}

                    {messages.map((msg, index) => (
                        <View
                            key={index}
                            style={[
                                styles.messageBubble,
                                msg.role === 'user' ? styles.userBubble : styles.assistantBubble,
                            ]}
                        >
                            {msg.role === 'assistant' && (
                                <View style={styles.assistantIcon}>
                                    <Bot size={16} color={COLORS.primary} />
                                </View>
                            )}
                            <Text
                                style={[
                                    styles.messageText,
                                    msg.role === 'user' && styles.userMessageText,
                                ]}
                            >
                                {msg.content}
                            </Text>
                        </View>
                    ))}

                    {loading && (
                        <View style={styles.loadingBubble}>
                            <ActivityIndicator size="small" color={COLORS.primary} />
                            <Text style={styles.loadingText}>Düşünüyorum...</Text>
                        </View>
                    )}
                </ScrollView>

                {/* Suggestions */}
                {suggestions.length > 0 && (
                    <View style={styles.suggestionsContainer}>
                        {suggestions.map((suggestion, index) => (
                            <TouchableOpacity
                                key={index}
                                style={styles.suggestionButton}
                                onPress={() => sendMessage(suggestion)}
                            >
                                <Text style={styles.suggestionText}>{suggestion}</Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                )}

                {/* Input */}
                <View style={styles.inputContainer}>
                    <TextInput
                        style={styles.input}
                        placeholder="Mesajınızı yazın..."
                        placeholderTextColor={COLORS.textSecondary}
                        value={inputText}
                        onChangeText={setInputText}
                        multiline
                        maxLength={2000}
                        editable={!loading}
                    />
                    <TouchableOpacity
                        style={[styles.sendButton, (!inputText.trim() || loading) && styles.sendButtonDisabled]}
                        onPress={() => sendMessage()}
                        disabled={!inputText.trim() || loading}
                    >
                        <Send size={20} color={inputText.trim() && !loading ? COLORS.background : COLORS.textSecondary} />
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>
        </Modal>
    );
};

// Floating Action Button for Chat
interface HocaFABProps {
    onPress: () => void;
}

export const HocaFAB: React.FC<HocaFABProps> = ({ onPress }) => (
    <TouchableOpacity style={styles.fab} onPress={onPress}>
        <MessageCircle size={24} color={COLORS.background} />
    </TouchableOpacity>
);

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: COLORS.background,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: COLORS.surfaceLight,
    },
    headerTitle: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    avatar: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: COLORS.primary,
        justifyContent: 'center',
        alignItems: 'center',
    },
    title: {
        color: COLORS.text,
        fontSize: 18,
        fontWeight: '700',
    },
    subtitle: {
        color: COLORS.textSecondary,
        fontSize: 13,
    },
    closeButton: {
        padding: 8,
    },
    messagesContainer: {
        flex: 1,
    },
    messagesContent: {
        padding: 16,
        paddingBottom: 32,
    },
    emptyState: {
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 60,
    },
    emptyTitle: {
        color: COLORS.text,
        fontSize: 24,
        fontWeight: '700',
        marginTop: 16,
        marginBottom: 8,
    },
    emptyText: {
        color: COLORS.textSecondary,
        fontSize: 15,
        textAlign: 'center',
        lineHeight: 22,
    },
    messageBubble: {
        maxWidth: '80%',
        padding: 12,
        borderRadius: 16,
        marginBottom: 12,
    },
    userBubble: {
        alignSelf: 'flex-end',
        backgroundColor: COLORS.primary,
        borderBottomRightRadius: 4,
    },
    assistantBubble: {
        alignSelf: 'flex-start',
        backgroundColor: COLORS.surface,
        borderBottomLeftRadius: 4,
        flexDirection: 'row',
        alignItems: 'flex-start',
    },
    assistantIcon: {
        marginRight: 8,
        marginTop: 2,
    },
    messageText: {
        color: COLORS.text,
        fontSize: 15,
        lineHeight: 22,
        flex: 1,
    },
    userMessageText: {
        color: COLORS.background,
    },
    loadingBubble: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        padding: 12,
        backgroundColor: COLORS.surface,
        borderRadius: 16,
        alignSelf: 'flex-start',
    },
    loadingText: {
        color: COLORS.textSecondary,
        fontSize: 14,
    },
    suggestionsContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        paddingHorizontal: 16,
        paddingBottom: 8,
        gap: 8,
    },
    suggestionButton: {
        backgroundColor: COLORS.surfaceLight,
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: COLORS.primary + '40',
    },
    suggestionText: {
        color: COLORS.primary,
        fontSize: 13,
    },
    inputContainer: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        padding: 12,
        borderTopWidth: 1,
        borderTopColor: COLORS.surfaceLight,
        gap: 8,
    },
    input: {
        flex: 1,
        backgroundColor: COLORS.surface,
        borderRadius: 20,
        paddingHorizontal: 16,
        paddingVertical: 10,
        color: COLORS.text,
        fontSize: 15,
        maxHeight: 100,
    },
    sendButton: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: COLORS.primary,
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendButtonDisabled: {
        backgroundColor: COLORS.surfaceLight,
    },
    fab: {
        position: 'absolute',
        right: 16,
        bottom: 80,
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: COLORS.primary,
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: COLORS.primary,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 8,
    },
});

export default HocaChatModal;
