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
import { MessageCircle, X, Send, Bot, User, Sparkles, Brain, Loader } from 'lucide-react-native';

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
    const [deepLearning, setDeepLearning] = useState(false);
    const scrollViewRef = useRef<ScrollView>(null);

    // Deep Learning - Analyze all training history
    const runDeepLearning = async () => {
        setDeepLearning(true);
        try {
            const response = await fetch('http://localhost:8000/coach/learn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force: true }),
            });
            const data = await response.json();

            // Add result as message
            const resultMessage: Message = {
                role: 'assistant',
                content: `🎓 **Derin Analiz Tamamlandı!**\n\n${data.activities_analyzed} antrenman analiz edildi.\n\n${data.facts_extracted?.substring(0, 500)}...`,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, resultMessage]);
        } catch (error) {
            const errorMessage: Message = {
                role: 'assistant',
                content: '⚠️ Derin analiz sırasında bir hata oluştu.',
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setDeepLearning(false);
        }
    };

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
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);
        setInputText('');
        setLoading(true);
        setSuggestions([]);

        try {
            // Build conversation history for context (last 6 messages)
            const conversationHistory = updatedMessages.slice(-6).map(msg => ({
                role: msg.role,
                content: msg.content
            }));

            // Coach V2 endpoint with conversation history
            const response = await fetch('http://localhost:8000/api/coach/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 1,  // TODO: Get from auth context
                    message: messageText,
                    garmin_activity_id: activityId || undefined,
                    debug: false,
                    conversation_history: conversationHistory,
                }),
            });

            const data = await response.json();

            // Track resolved activity ID for future messages
            if (data.resolved_activity_id && !activityId) {
                // Optionally update activityId state if you want to persist context
                // setActivityId(data.resolved_activity_id);
            }

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
                    <View style={styles.headerActions}>
                        <TouchableOpacity
                            onPress={runDeepLearning}
                            style={[styles.deepLearnButton, deepLearning && styles.deepLearnButtonActive]}
                            disabled={deepLearning}
                        >
                            {deepLearning ? (
                                <Loader size={18} color={COLORS.primary} />
                            ) : (
                                <Brain size={18} color={COLORS.primary} />
                            )}
                            <Text style={styles.deepLearnText}>
                                {deepLearning ? 'Analiz...' : 'Öğren'}
                            </Text>
                        </TouchableOpacity>
                        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                            <X size={24} color={COLORS.text} />
                        </TouchableOpacity>
                    </View>
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
    headerActions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    deepLearnButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: COLORS.primary + '60',
        backgroundColor: COLORS.surface,
    },
    deepLearnButtonActive: {
        borderColor: COLORS.primary,
        backgroundColor: COLORS.surfaceLight,
    },
    deepLearnText: {
        color: COLORS.primary,
        fontSize: 13,
        fontWeight: '600',
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
