import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Brain, ChevronRight, Activity, Calendar, Clock } from 'lucide-react-native';
import { useDashboardStore } from '../../store/useDashboardStore';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const ContextScreen = () => {
    const navigation = useNavigation<any>();
    const userProfile = useDashboardStore(state => state.userProfile);
    const setGoals = useDashboardStore(state => state.setGoals);

    const [selectedDays, setSelectedDays] = useState<string[]>([]);
    const [longRunDay, setLongRunDay] = useState<string>('');
    const [experience, setExperience] = useState('Intermediate');

    const stressLevel = userProfile.stressScore || 25;

    const getStressLabel = (score: number) => {
        if (score < 25) return { label: 'Low', color: '#00FF99' };
        if (score < 50) return { label: 'Moderate', color: '#FFCC00' };
        return { label: 'High', color: '#FF3333' };
    };

    const stressInfo = getStressLabel(stressLevel);

    const toggleDay = (day: string) => {
        if (selectedDays.includes(day)) {
            const newDays = selectedDays.filter(d => d !== day);
            setSelectedDays(newDays);
            if (longRunDay === day) setLongRunDay(''); // Reset long run if day is removed
        } else {
            setSelectedDays([...selectedDays, day]);
        }
    };

    const handleNext = () => {
        if (selectedDays.length === 0) {
            alert("Please select at least one training day.");
            return;
        }
        if (!longRunDay) {
            alert("Please select a day for your Long Run.");
            return;
        }

        setGoals({
            trainingDays: selectedDays,
            longRunDay: longRunDay,
            experienceLevel: experience
        });

        navigation.navigate('Goals');
    };

    return (
        <ScrollView contentContainerStyle={styles.container}>
            <View style={styles.header}>
                <Brain color="#CCFF00" size={48} />
                <Text style={styles.title}>The Context</Text>
                <Text style={styles.subtitle}>
                    Your physiology is only half the story. Let's factor in your life schedule.
                </Text>
            </View>

            {/* Stress Card */}
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <Activity color={stressInfo.color} size={24} />
                    <Text style={styles.cardTitle}>Life Stress Load</Text>
                </View>
                <View style={styles.stressContainer}>
                    <Text style={[styles.stressValue, { color: stressInfo.color }]}>{stressLevel}</Text>
                    <Text style={[styles.stressLabel, { color: stressInfo.color }]}>{stressInfo.label}</Text>
                </View>
                <Text style={styles.stressAdvice}>
                    {stressLevel > 50
                        ? "High life stress. We'll adjust intensity to prevent burnout."
                        : "Stress is manageable. Ready for optimal loading."}
                </Text>
            </View>

            {/* Weekly Schedule */}
            <View style={styles.section}>
                <View style={styles.sectionHeader}>
                    <Calendar color="#666" size={20} />
                    <Text style={styles.sectionTitle}>Weekly Schedule</Text>
                </View>
                <Text style={styles.sectionDesc}>Tap the days you can train.</Text>

                <View style={styles.daysGrid}>
                    {DAYS.map(day => {
                        const isSelected = selectedDays.includes(day);
                        return (
                            <TouchableOpacity
                                key={day}
                                style={[styles.dayButton, isSelected && styles.dayButtonActive]}
                                onPress={() => toggleDay(day)}
                            >
                                <Text style={[styles.dayText, isSelected && styles.dayTextActive]}>{day}</Text>
                            </TouchableOpacity>
                        );
                    })}
                </View>
            </View>

            {/* Long Run Day */}
            {selectedDays.length > 0 && (
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <Clock color="#666" size={20} />
                        <Text style={styles.sectionTitle}>Long Run Day</Text>
                    </View>
                    <Text style={styles.sectionDesc}>Which of your training days is best for a long session?</Text>

                    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.longRunScroll}>
                        {selectedDays.map(day => (
                            <TouchableOpacity
                                key={day}
                                style={[styles.longRunButton, longRunDay === day && styles.longRunButtonActive]}
                                onPress={() => setLongRunDay(day)}
                            >
                                <Text style={[styles.longRunText, longRunDay === day && styles.longRunTextActive]}>
                                    {day}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </ScrollView>
                </View>
            )}

            {/* Experience Level */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Experience Level</Text>
                <View style={styles.expRow}>
                    {['Beginner', 'Intermediate', 'Advanced'].map(level => (
                        <TouchableOpacity
                            key={level}
                            style={[styles.expButton, experience === level && styles.expButtonActive]}
                            onPress={() => setExperience(level)}
                        >
                            <Text style={[styles.expText, experience === level && styles.expTextActive]}>{level}</Text>
                        </TouchableOpacity>
                    ))}
                </View>
            </View>

            <TouchableOpacity style={styles.nextButton} onPress={handleNext}>
                <Text style={styles.nextButtonText}>Next: AI Coach</Text>
                <ChevronRight color="#050505" size={24} />
            </TouchableOpacity>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        backgroundColor: '#050505',
        padding: 24,
        paddingTop: 60,
    },
    header: { marginBottom: 30 },
    title: { color: 'white', fontSize: 32, fontWeight: 'bold', marginTop: 16, marginBottom: 8 },
    subtitle: { color: '#888', fontSize: 16, lineHeight: 24 },

    card: {
        backgroundColor: '#1A1A1A',
        padding: 20,
        borderRadius: 16,
        marginBottom: 32,
        borderWidth: 1,
        borderColor: '#333',
    },
    cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 8 },
    cardTitle: { color: 'white', fontSize: 18, fontWeight: 'bold' },
    stressContainer: { flexDirection: 'row', alignItems: 'baseline', gap: 12, marginBottom: 8 },
    stressValue: { fontSize: 32, fontWeight: 'bold' },
    stressLabel: { fontSize: 18, fontWeight: '600' },
    stressAdvice: { color: '#CCC', fontSize: 14 },

    section: { marginBottom: 32 },
    sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
    sectionTitle: { color: '#CCC', fontSize: 16, fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 1 },
    sectionDesc: { color: '#666', fontSize: 14, marginBottom: 16 },

    daysGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 10,
    },
    dayButton: {
        width: '13%', // Approx for 7 items with gap
        aspectRatio: 1,
        borderRadius: 20, // Circle-ish
        backgroundColor: '#111',
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#333',
    },
    dayButtonActive: { backgroundColor: '#CCFF00', borderColor: '#CCFF00' },
    dayText: { color: '#666', fontWeight: 'bold', fontSize: 12 },
    dayTextActive: { color: '#050505' },

    longRunScroll: { flexDirection: 'row' },
    longRunButton: {
        paddingVertical: 12,
        paddingHorizontal: 24,
        backgroundColor: '#111',
        borderRadius: 24,
        marginRight: 10,
        borderWidth: 1,
        borderColor: '#333',
    },
    longRunButtonActive: { backgroundColor: '#00CCFF', borderColor: '#00CCFF' },
    longRunText: { color: '#888', fontWeight: '600' },
    longRunTextActive: { color: '#050505', fontWeight: 'bold' },

    expRow: { flexDirection: 'row', gap: 10 },
    expButton: {
        flex: 1,
        paddingVertical: 16,
        backgroundColor: '#111',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#333',
        alignItems: 'center',
    },
    expButtonActive: { backgroundColor: '#CCFF00', borderColor: '#CCFF00' },
    expText: { color: '#888', fontWeight: '600', fontSize: 12 },
    expTextActive: { color: '#050505' },

    nextButton: {
        backgroundColor: '#CCFF00',
        height: 56,
        borderRadius: 12,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 8,
        marginBottom: 40,
    },
    nextButtonText: { color: '#050505', fontSize: 18, fontWeight: 'bold' },
});

export default ContextScreen;
