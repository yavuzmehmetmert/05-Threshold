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
import { MessageCircle, X, Send, Bot, User, Sparkles, Brain, Loader, Eye, EyeOff } from 'lucide-react-native';

const COLORS = {
    background: '#050505',
    surface: '#1A1A1A',
    surfaceLight: '#2A2A2A',
    primary: '#CCFF00',
    text: '#FFFFFF',
    textSecondary: '#888888',
    error: '#FF3333',
};

interface DebugStep {
    step: number;
    name: string;
    description?: string;
    prompt_sent?: string;
    llm_response?: string;
    extracted_sql?: string;
    sql?: string;
    is_valid?: boolean;
    result_count?: number;
    sample_results?: any[];
    status: string;
    error?: string;
    activity_context?: string;  // Activity data loaded
    context_preview?: string;   // Context for trend/health
    data_source?: string;       // Where data came from
    // Execution plan fields
    thought_process?: string;   // Planner's reasoning
    plan?: {                    // Planned steps
        step: number;
        handler: string;
        description?: string;
        entities?: any;
        depends_on?: number | number[] | null;
    }[];
    // Enhanced debug fields
    data_preview?: string;              // Table-style data preview
    data_summary?: string;              // Brief data summary
    raw_data_keys?: string[];           // Keys in raw data
    has_data_context?: boolean;         // Whether data context was used
    previous_context_preview?: string;  // Preview of context from previous handlers
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    debug_steps?: DebugStep[];  // SQL Agent debug info
}

interface HocaChatModalProps {
    visible: boolean;
    onClose: () => void;
    activityId?: number; // If opened from activity detail
    initialMessage?: string;
    onNavigateToActivity?: (activityId: number) => void; // Callback for activity link clicks
}

export const HocaChatModal: React.FC<HocaChatModalProps> = ({
    visible,
    onClose,
    activityId,
    initialMessage,
    onNavigateToActivity,
}) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [deepLearning, setDeepLearning] = useState(false);
    const [showDebug, setShowDebug] = useState(false);
    const scrollViewRef = useRef<ScrollView>(null);

    // Parse activity links [text](activity://ID) and make them clickable
    const renderLinkifiedText = (text: string) => {
        // Regex to match [link text](activity://activityId)
        const linkRegex = /\[([^\]]+)\]\(activity:\/\/(\d+)\)/g;
        const parts: React.ReactNode[] = [];
        let lastIndex = 0;
        let match;

        while ((match = linkRegex.exec(text)) !== null) {
            // Add text before the link
            if (match.index > lastIndex) {
                parts.push(text.substring(lastIndex, match.index));
            }

            // Add the clickable link
            const linkText = match[1];
            const actId = parseInt(match[2], 10);
            parts.push(
                <Text
                    key={match.index}
                    style={styles.activityLink}
                    onPress={() => {
                        if (onNavigateToActivity) {
                            onClose(); // Close modal first
                            onNavigateToActivity(actId);
                        }
                    }}
                >
                    {linkText}
                </Text>
            );

            lastIndex = match.index + match[0].length;
        }

        // Add remaining text after last link
        if (lastIndex < text.length) {
            parts.push(text.substring(lastIndex));
        }

        return parts.length > 0 ? parts : text;
    };

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
                    debug: true,
                    conversation_history: conversationHistory,
                }),
            });

            const data = await response.json();

            // Track resolved activity ID for future messages
            if (data.resolved_activity_id && !activityId) {
                // Optionally update activityId state if you want to persist context
                // setActivityId(data.resolved_activity_id);
            }

            // Add assistant message with debug info
            const assistantMessage: Message = {
                role: 'assistant',
                content: data.message || 'Bir hata oluştu.',
                timestamp: new Date(),
                debug_steps: data.debug_steps || undefined,
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
                            onPress={() => setShowDebug(!showDebug)}
                            style={[styles.debugToggleButton, showDebug && styles.debugToggleButtonActive]}
                        >
                            {showDebug ? (
                                <Eye size={18} color={COLORS.primary} />
                            ) : (
                                <EyeOff size={18} color={COLORS.textSecondary} />
                            )}
                        </TouchableOpacity>
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
                        <View key={index}>
                            <View
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
                                    {msg.role === 'assistant'
                                        ? renderLinkifiedText(msg.content)
                                        : msg.content}
                                </Text>
                            </View>

                            {/* Debug Panel - Conditional */}
                            {showDebug && msg.debug_steps && msg.debug_steps.length > 0 && (
                                <View style={styles.debugPanel}>
                                    <Text style={styles.debugTitle}>🔍 Debug (SQL Agent)</Text>
                                    {msg.debug_steps.map((step, stepIdx) => (
                                        <View key={stepIdx} style={styles.debugStep}>
                                            {/* Special rendering for EXECUTION PLAN (step 0) */}
                                            {step.name === '📋 EXECUTION PLAN' && step.plan ? (
                                                <View>
                                                    <Text style={styles.debugStepName}>
                                                        {step.name} [{step.status}]
                                                    </Text>
                                                    <Text style={styles.debugDescription}>
                                                        {step.description}
                                                    </Text>

                                                    {/* Thought Process */}
                                                    {step.thought_process && (
                                                        <View style={styles.planThought}>
                                                            <Text style={styles.planThoughtLabel}>💭 Düşünce:</Text>
                                                            <Text style={styles.planThoughtText}>{step.thought_process}</Text>
                                                        </View>
                                                    )}

                                                    {/* Plan Steps */}
                                                    <View style={styles.planSteps}>
                                                        <Text style={styles.planStepsLabel}>📋 Plan:</Text>
                                                        {step.plan.map((planStep: any, planIdx: number) => (
                                                            <View key={planIdx} style={styles.planStepItem}>
                                                                <Text style={styles.planStepNumber}>
                                                                    Step {planStep.step}:
                                                                </Text>
                                                                <Text style={styles.planStepHandler}>
                                                                    {planStep.handler}
                                                                </Text>
                                                                {planStep.description && planStep.description !== `Execute ${planStep.handler}` && (
                                                                    <Text style={styles.planStepDesc}>
                                                                        → {planStep.description}
                                                                    </Text>
                                                                )}
                                                                {planStep.depends_on && planStep.depends_on !== -1 && (
                                                                    <Text style={styles.planStepDeps}>
                                                                        (depends: {Array.isArray(planStep.depends_on) ? planStep.depends_on.join(', ') : planStep.depends_on})
                                                                    </Text>
                                                                )}
                                                            </View>
                                                        ))}
                                                    </View>
                                                </View>
                                            ) : (
                                                /* Regular step rendering */
                                                <View>
                                                    <Text style={styles.debugStepName}>
                                                        Step {step.step}: {step.name} [{step.status}]
                                                    </Text>

                                                    {/* Description - Shows Gemini vs Fallback */}
                                                    {step.description && (
                                                        <Text style={styles.debugDescription}>
                                                            {step.description}
                                                        </Text>
                                                    )}
                                                </View>
                                            )}

                                            {/* Prompt Sent to Gemini */}
                                            {step.prompt_sent && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>📤 Prompt Gönderildi:</Text>
                                                    <Text style={styles.debugPrompt}>
                                                        {step.prompt_sent}
                                                    </Text>
                                                </View>
                                            )}

                                            {/* LLM Response */}
                                            {step.llm_response && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabelGreen}>📥 Gemini Cevabı:</Text>
                                                    <Text style={styles.debugResponse}>
                                                        {step.llm_response}
                                                    </Text>
                                                </View>
                                            )}

                                            {/* Extracted SQL */}
                                            {step.extracted_sql && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>🔧 Çıkarılan SQL:</Text>
                                                    <Text style={styles.debugSql}>{step.extracted_sql}</Text>
                                                </View>
                                            )}

                                            {/* SQL Query (from lookup handler) */}
                                            {step.sql && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>🔍 Lookup SQL:</Text>
                                                    <ScrollView style={styles.debugScrollArea} nestedScrollEnabled={true} horizontal>
                                                        <Text style={styles.debugSql}>{step.sql}</Text>
                                                    </ScrollView>
                                                </View>
                                            )}

                                            {/* Result count */}
                                            {step.result_count !== undefined && (
                                                <Text style={styles.debugInfo}>📊 Results: {step.result_count} rows</Text>
                                            )}

                                            {/* Sample Results (top 5 from lookup) */}
                                            {step.sample_results && step.sample_results.length > 0 && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabelGreen}>📋 İlk 5 Sonuç:</Text>
                                                    <ScrollView style={styles.debugScrollArea} nestedScrollEnabled={true}>
                                                        {step.sample_results.map((result: any, idx: number) => (
                                                            <Text key={idx} style={styles.debugInfo}>
                                                                {idx + 1}. {result.activity_name} ({result.date})
                                                                {result.weather_temp && ` - ${result.weather_temp}`}
                                                                {result.avg_speed && ` - ${result.avg_speed}`}
                                                                {result.distance && ` - ${result.distance}`}
                                                                {result.training_effect && ` - TE: ${result.training_effect}`}
                                                                {result.max_hr && ` - ${result.max_hr}`}
                                                            </Text>
                                                        ))}
                                                    </ScrollView>
                                                </View>
                                            )}

                                            {/* Data Summary (brief) */}
                                            {step.data_summary && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>📊 Veri Özeti:</Text>
                                                    <Text style={styles.debugInfo}>{step.data_summary}</Text>
                                                </View>
                                            )}

                                            {/* Data Preview (detailed table) */}
                                            {step.data_preview && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabelGreen}>📋 Detaylı Veri:</Text>
                                                    <Text style={styles.debugDataPreview}>
                                                        {step.data_preview}
                                                    </Text>
                                                </View>
                                            )}

                                            {/* Previous Context Preview (what sohbet_handler received) */}
                                            {step.previous_context_preview && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>📥 LLM'e Gönderilen Veri:</Text>
                                                    <ScrollView style={styles.debugScrollArea} nestedScrollEnabled={true}>
                                                        <Text style={styles.debugPrompt}>
                                                            {step.previous_context_preview}
                                                        </Text>
                                                    </ScrollView>
                                                </View>
                                            )}

                                            {/* Activity Context Data */}
                                            {step.activity_context && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>📋 Activity Data:</Text>
                                                    <ScrollView style={styles.debugScrollArea} nestedScrollEnabled={true}>
                                                        <Text style={styles.debugPrompt}>
                                                            {step.activity_context}
                                                        </Text>
                                                    </ScrollView>
                                                </View>
                                            )}

                                            {/* Context Preview (for trend/health) */}
                                            {step.context_preview && (
                                                <View style={styles.debugCode}>
                                                    <Text style={styles.debugLabel}>📋 Context Data:</Text>
                                                    <Text style={styles.debugPrompt} numberOfLines={6}>
                                                        {step.context_preview}
                                                    </Text>
                                                </View>
                                            )}

                                            {/* Error */}
                                            {step.error && (
                                                <Text style={styles.debugError}>❌ Error: {step.error}</Text>
                                            )}
                                        </View>
                                    ))}
                                </View>
                            )}
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
    debugToggleButton: {
        padding: 8,
        borderRadius: 8,
    },
    debugToggleButtonActive: {
        backgroundColor: COLORS.surfaceLight,
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
    // Debug Panel Styles
    debugPanel: {
        marginLeft: 12,
        marginTop: 4,
        marginBottom: 8,
        padding: 12,
        backgroundColor: '#0D1117',
        borderRadius: 8,
        borderLeftWidth: 3,
        borderLeftColor: '#58A6FF',
    },
    debugTitle: {
        color: '#58A6FF',
        fontSize: 13,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    debugStep: {
        marginBottom: 10,
        paddingBottom: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#21262D',
    },
    debugStepName: {
        color: '#8B949E',
        fontSize: 12,
        fontWeight: '600',
        marginBottom: 4,
    },
    debugDescription: {
        color: '#58A6FF',
        fontSize: 11,
        marginBottom: 6,
        fontStyle: 'italic',
    },
    debugCode: {
        backgroundColor: '#161B22',
        padding: 8,
        borderRadius: 4,
        marginTop: 4,
    },
    debugLabel: {
        color: '#7EE787',
        fontSize: 10,
        fontWeight: 'bold',
        marginBottom: 2,
    },
    debugSql: {
        color: '#F0883E',
        fontSize: 11,
        fontFamily: 'monospace',
    },
    debugInfo: {
        color: '#8B949E',
        fontSize: 11,
        marginTop: 4,
    },
    debugError: {
        color: '#F85149',
        fontSize: 11,
        marginTop: 4,
    },
    debugPrompt: {
        color: '#C9D1D9',
        fontSize: 10,
        fontFamily: 'monospace',
        marginTop: 2,
    },
    debugLabelGreen: {
        color: '#7EE787',
        fontSize: 10,
        fontWeight: 'bold',
        marginBottom: 2,
    },
    debugResponse: {
        color: '#A5D6FF',
        fontSize: 10,
        fontFamily: 'monospace',
        marginTop: 2,
    },
    // Plan visualization styles
    planThought: {
        backgroundColor: '#1a2a3a',
        padding: 8,
        borderRadius: 4,
        marginTop: 8,
        marginBottom: 8,
    },
    planThoughtLabel: {
        color: '#FFD700',
        fontSize: 11,
        fontWeight: 'bold',
        marginBottom: 4,
    },
    planThoughtText: {
        color: '#CCCCCC',
        fontSize: 11,
        fontStyle: 'italic',
    },
    planSteps: {
        backgroundColor: '#0d1117',
        borderRadius: 4,
        padding: 8,
        marginTop: 8,
    },
    planStepsLabel: {
        color: '#CCFF00',
        fontSize: 12,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    planStepItem: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        alignItems: 'center',
        paddingVertical: 4,
        paddingLeft: 8,
        borderLeftWidth: 2,
        borderLeftColor: '#CCFF00',
        marginBottom: 6,
    },
    planStepNumber: {
        color: '#CCFF00',
        fontSize: 11,
        fontWeight: 'bold',
        marginRight: 6,
    },
    planStepHandler: {
        color: '#58A6FF',
        fontSize: 11,
        fontWeight: 'bold',
    },
    planStepDesc: {
        color: '#8B949E',
        fontSize: 10,
        marginLeft: 8,
        flexBasis: '100%',
        marginTop: 2,
    },
    planStepDeps: {
        color: '#7C3AED',
        fontSize: 9,
        marginLeft: 8,
    },
    debugDataPreview: {
        color: '#58A6FF',
        fontSize: 9,
        fontFamily: 'monospace',
        marginTop: 4,
        backgroundColor: '#161b22',
        padding: 8,
        borderRadius: 4,
        lineHeight: 14,
    },
    debugScrollArea: {
        maxHeight: 300,
        backgroundColor: '#161b22',
        borderRadius: 4,
        marginTop: 4,
    },
    activityLink: {
        color: '#CCFF00',
        textDecorationLine: 'underline' as const,
        fontWeight: 'bold' as const,
    },
});

export default HocaChatModal;
