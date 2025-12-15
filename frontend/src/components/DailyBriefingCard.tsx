import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { Sun, RefreshCw } from 'lucide-react-native';

const API_BASE = 'http://localhost:8000';

interface Props {
    userId: number;
    date?: string; // YYYY-MM-DD format, defaults to today
}

/**
 * DailyBriefingCard
 * 
 * Displays the morning coaching briefing for a user.
 * Fetches from /api/coach/briefing endpoint.
 */
export const DailyBriefingCard: React.FC<Props> = ({ userId, date }) => {
    const [briefing, setBriefing] = useState('');
    const [briefingDate, setBriefingDate] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchBriefing = async () => {
        setLoading(true);
        setError('');

        try {
            const url = new URL(`${API_BASE}/api/coach/briefing`);
            url.searchParams.set('user_id', String(userId));
            if (date) {
                url.searchParams.set('date_str', date);
            }

            const res = await fetch(url.toString());

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            const data = await res.json();
            setBriefing(data.briefing_text);
            setBriefingDate(data.briefing_date);
        } catch (e: any) {
            setError(e.message || 'Failed to load briefing');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchBriefing();
    }, [userId, date]);

    const formatDate = (dateStr: string) => {
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString('tr-TR', {
                weekday: 'long',
                day: 'numeric',
                month: 'long'
            });
        } catch {
            return dateStr;
        }
    };

    if (loading) {
        return (
            <View style={styles.card}>
                <ActivityIndicator size="large" color="#4CAF50" />
                <Text style={styles.loadingText}>Günlük brifing yükleniyor...</Text>
            </View>
        );
    }

    if (error) {
        return (
            <View style={[styles.card, styles.errorCard]}>
                <Text style={styles.errorText}>⚠️ {error}</Text>
                <TouchableOpacity style={styles.retryButton} onPress={fetchBriefing}>
                    <RefreshCw size={16} color="#fff" />
                    <Text style={styles.retryText}>Tekrar Dene</Text>
                </TouchableOpacity>
            </View>
        );
    }

    return (
        <View style={styles.card}>
            <View style={styles.header}>
                <View style={styles.headerLeft}>
                    <Sun size={24} color="#FFA000" />
                    <Text style={styles.headerTitle}>Günlük Brifing</Text>
                </View>
                <TouchableOpacity onPress={fetchBriefing}>
                    <RefreshCw size={18} color="#666" />
                </TouchableOpacity>
            </View>

            <Text style={styles.dateText}>{formatDate(briefingDate)}</Text>

            <View style={styles.content}>
                <Text style={styles.briefingText}>{briefing}</Text>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    card: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 20,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
        elevation: 4,
        marginHorizontal: 16,
        marginVertical: 8,
    },
    errorCard: {
        borderWidth: 1,
        borderColor: '#ffcdd2',
        backgroundColor: '#fff5f5',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    headerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: '#333',
    },
    dateText: {
        fontSize: 13,
        color: '#666',
        marginBottom: 12,
        textTransform: 'capitalize',
    },
    content: {
        backgroundColor: '#f8f9fa',
        borderRadius: 12,
        padding: 16,
    },
    briefingText: {
        fontSize: 15,
        lineHeight: 24,
        color: '#333',
    },
    loadingText: {
        marginTop: 12,
        color: '#666',
        textAlign: 'center',
    },
    errorText: {
        color: '#d32f2f',
        marginBottom: 12,
    },
    retryButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#4CAF50',
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 8,
        gap: 6,
    },
    retryText: {
        color: '#fff',
        fontWeight: '600',
    },
});

export default DailyBriefingCard;
