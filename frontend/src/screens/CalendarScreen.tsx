import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Dimensions } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ChevronLeft, ChevronRight, Activity, Calendar as CalendarIcon, MapPin, Clock, Flame, Zap } from 'lucide-react-native';
import { useDashboardStore } from '../store/useDashboardStore';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const CalendarScreen = () => {
    const navigation = useNavigation<any>();
    const activities = useDashboardStore(state => state.activities);
    const setActivities = useDashboardStore(state => state.setActivities);

    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState(new Date());

    useEffect(() => {
        fetchActivities();
    }, []);

    const fetchActivities = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/activities?limit=50');
            if (response.ok) {
                const data = await response.json();
                setActivities(data);
            }
        } catch (error) {
            console.error('Failed to fetch activities:', error);
        }
    };

    const getDaysInMonth = (date: Date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        return new Date(year, month + 1, 0).getDate();
    };

    const getFirstDayOfMonth = (date: Date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const day = new Date(year, month, 1).getDay();
        return day === 0 ? 6 : day - 1; // Adjust for Mon start
    };

    const changeMonth = (increment: number) => {
        const newDate = new Date(currentDate);
        newDate.setMonth(newDate.getMonth() + increment);
        setCurrentDate(newDate);
    };

    const renderCalendarGrid = () => {
        const daysInMonth = getDaysInMonth(currentDate);
        const firstDay = getFirstDayOfMonth(currentDate);
        const days = [];

        // Empty cells for previous month
        for (let i = 0; i < firstDay; i++) {
            days.push(<View key={`empty-${i}`} style={styles.dayCell} />);
        }

        // Days of current month
        for (let i = 1; i <= daysInMonth; i++) {
            const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
            const dayActivities = activities.filter(a => a.startTimeLocal.startsWith(dateStr));
            const isSelected = selectedDate.getDate() === i && selectedDate.getMonth() === currentDate.getMonth() && selectedDate.getFullYear() === currentDate.getFullYear();

            days.push(
                <TouchableOpacity
                    key={i}
                    style={[styles.dayCell, isSelected && styles.selectedDayCell]}
                    onPress={() => setSelectedDate(new Date(currentDate.getFullYear(), currentDate.getMonth(), i))}
                >
                    <Text style={[styles.dayText, isSelected && styles.selectedDayText]}>{i}</Text>
                    <View style={styles.activityDots}>
                        {dayActivities.map((act, index) => (
                            <View key={index} style={[styles.dot, { backgroundColor: getActivityColor(act.activityType) }]} />
                        ))}
                    </View>
                </TouchableOpacity>
            );
        }

        return days;
    };

    const getActivityColor = (type: string) => {
        if (type.includes('running')) return '#CCFF00';
        if (type.includes('cycling')) return '#00CCFF';
        if (type.includes('swimming')) return '#CC00FF';
        return '#888';
    };

    const getActivityIcon = (type: string) => {
        // Simple icon mapping, can be expanded
        return Activity;
    };

    const selectedDateStr = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;
    const selectedActivities = activities.filter(a => a.startTimeLocal.startsWith(selectedDateStr));

    return (
        <ScrollView contentContainerStyle={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => changeMonth(-1)}>
                    <ChevronLeft color="#CCFF00" size={24} />
                </TouchableOpacity>
                <Text style={styles.monthTitle}>
                    {MONTHS[currentDate.getMonth()]} {currentDate.getFullYear()}
                </Text>
                <TouchableOpacity onPress={() => changeMonth(1)}>
                    <ChevronRight color="#CCFF00" size={24} />
                </TouchableOpacity>
            </View>

            <View style={styles.weekDays}>
                {DAYS.map(day => (
                    <Text key={day} style={styles.weekDayText}>{day}</Text>
                ))}
            </View>

            <View style={styles.calendarGrid}>
                {renderCalendarGrid()}
            </View>

            <View style={styles.detailsSection}>
                <Text style={styles.detailsTitle}>
                    Activities for {selectedDate.toDateString()}
                </Text>

                {selectedActivities.length > 0 ? (
                    selectedActivities.map(activity => (
                        <TouchableOpacity
                            key={activity.activityId}
                            style={styles.activityCard}
                            onPress={() => navigation.navigate('ActivityDetail', { activity })}
                        >
                            <View style={[styles.iconBox, { backgroundColor: getActivityColor(activity.activityType) + '20' }]}>
                                <Activity color={getActivityColor(activity.activityType)} size={24} />
                            </View>
                            <View style={styles.activityInfo}>
                                <Text style={styles.activityName}>{activity.activityName}</Text>
                                <Text style={styles.activityMeta}>
                                    {(activity.distance / 1000).toFixed(2)} km • {(activity.duration / 60).toFixed(0)} min
                                </Text>
                            </View>
                            <ChevronRight color="#666" size={20} />
                        </TouchableOpacity>
                    ))
                ) : (
                    <Text style={styles.noActivityText}>No activities recorded.</Text>
                )}
            </View>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    container: {
        flexGrow: 1,
        backgroundColor: '#050505',
        padding: 20,
        paddingTop: 60,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
    },
    monthTitle: {
        color: 'white',
        fontSize: 20,
        fontWeight: 'bold',
    },
    weekDays: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 10,
    },
    weekDayText: {
        color: '#666',
        width: '14%',
        textAlign: 'center',
        fontSize: 12,
        fontWeight: 'bold',
    },
    calendarGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        marginBottom: 30,
    },
    dayCell: {
        width: '14.28%',
        aspectRatio: 1,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 0.5,
        borderColor: '#111',
    },
    selectedDayCell: {
        backgroundColor: '#1A1A1A',
        borderRadius: 8,
        borderColor: '#CCFF00',
        borderWidth: 1,
    },
    dayText: {
        color: '#888',
        fontSize: 14,
    },
    selectedDayText: {
        color: 'white',
        fontWeight: 'bold',
    },
    activityDots: {
        flexDirection: 'row',
        gap: 4,
        marginTop: 6,
        justifyContent: 'center',
        flexWrap: 'wrap',
    },
    dot: {
        width: 10,
        height: 10,
        borderRadius: 5,
    },
    detailsSection: {
        marginTop: 10,
    },
    detailsTitle: {
        color: '#CCFF00',
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 16,
    },
    activityCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        padding: 16,
        borderRadius: 12,
        marginBottom: 12,
    },
    iconBox: {
        width: 40,
        height: 40,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
    },
    activityInfo: {
        flex: 1,
    },
    activityName: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
        marginBottom: 4,
    },
    activityMeta: {
        color: '#888',
        fontSize: 12,
    },
    noActivityText: {
        color: '#666',
        fontStyle: 'italic',
        textAlign: 'center',
        marginTop: 20,
    },
});

export default CalendarScreen;
