import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Dimensions, TextInput } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { ChevronLeft, ChevronRight, Activity, Calendar as CalendarIcon, MapPin, Clock, Flame, Zap, Search } from 'lucide-react-native';
import { useDashboardStore } from '../store/useDashboardStore';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const CalendarScreen = () => {
    const navigation = useNavigation<any>();
    const activities = useDashboardStore(state => state.activities);
    const setActivities = useDashboardStore(state => state.setActivities);

    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [searchText, setSearchText] = useState('');

    useEffect(() => {
        fetchActivities();
    }, []);

    const fetchActivities = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/activities?limit=1000');
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

    const getIntensityColor = (hr: number) => {
        const { userProfile } = useDashboardStore.getState();
        const maxHr = userProfile.maxHr || 190;

        if (!hr || hr === 0) return '#888'; // No data

        const pct = (hr / maxHr) * 100;

        // Intensity Logic
        if (pct < 75) return '#00CCFF'; // Easy / Recovery (Blue)
        if (pct < 85) return '#FFCC00'; // Moderate / Tempo (Yellow)
        return '#FF3333';               // Hard / Threshold+ (Red)
    };

    const renderCalendarGrid = () => {
        const daysInMonth = getDaysInMonth(currentDate);
        const firstDay = getFirstDayOfMonth(currentDate);
        const days = [];

        // Empty cells for previous month
        for (let i = 0; i < firstDay; i++) {
            days.push(<View key={`empty-${i}`} style={[styles.dayCell, styles.emptyCell]} />);
        }

        // Days of current month
        for (let i = 1; i <= daysInMonth; i++) {
            const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
            // Match substring (YYYY-MM-DD)
            const dayActivities = activities.filter(a => a.startTimeLocal && a.startTimeLocal.startsWith(dateStr));
            const isSelected = selectedDate.getDate() === i && selectedDate.getMonth() === currentDate.getMonth() && selectedDate.getFullYear() === currentDate.getFullYear();
            const isToday = new Date().getDate() === i && new Date().getMonth() === currentDate.getMonth() && new Date().getFullYear() === currentDate.getFullYear();

            days.push(
                <TouchableOpacity
                    key={i}
                    style={[styles.dayCell, isSelected && styles.selectedDayCell, isToday && styles.todayCell]}
                    onPress={() => setSelectedDate(new Date(currentDate.getFullYear(), currentDate.getMonth(), i))}
                >
                    <Text style={[styles.dayText, (isSelected || isToday) && styles.selectedDayText]}>{i}</Text>

                    {/* Activity Event Boxes */}
                    <View style={styles.eventContainer}>
                        {dayActivities.map((act, index) => {
                            const color = getIntensityColor(act.averageHeartRate);
                            return (
                                <TouchableOpacity
                                    key={index}
                                    style={[styles.eventBox, { borderColor: color, backgroundColor: color + '15' }]} // Outlined with slight tint
                                    onPress={() => navigation.navigate('ActivityDetail', { activity: act })}
                                >
                                    <Text style={[styles.eventName, { color: color }]} numberOfLines={1}>
                                        {act.activityName}
                                    </Text>
                                    <Text style={[styles.eventText, { color: color }]} numberOfLines={1}>
                                        {(act.distance / 1000).toFixed(1)}k
                                    </Text>
                                </TouchableOpacity>
                            );
                        })}
                    </View>
                </TouchableOpacity>
            );
        }

        return days;
    };

    const selectedDateStr = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`;


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

            {/* Search Bar */}
            <View style={styles.searchContainer}>
                <Search color="#666" size={20} style={{ marginRight: 10 }} />
                <TextInput
                    style={styles.searchInput}
                    placeholder="Search name or date (e.g. 2023-11)..."
                    placeholderTextColor="#666"
                    value={searchText}
                    onChangeText={setSearchText}
                />
            </View>

            {searchText.length > 0 && (
                <View style={[styles.detailsSection, { marginBottom: 20 }]}>
                    <Text style={styles.detailsTitle}>
                        Search Results "{searchText}"
                    </Text>

                    {(() => {
                        const selectedActivities = activities.filter(a =>
                            a.activityName.toLowerCase().includes(searchText.toLowerCase()) ||
                            (a.startTimeLocal && a.startTimeLocal.includes(searchText))
                        );

                        return selectedActivities.length > 0 ? (
                            selectedActivities.map(activity => (
                                <TouchableOpacity
                                    key={activity.activityId}
                                    style={styles.activityCard}
                                    onPress={() => navigation.navigate('ActivityDetail', { activity })}
                                >
                                    <View style={[styles.iconBox, { backgroundColor: getIntensityColor(activity.averageHeartRate) + '20' }]}>
                                        <Activity color={getIntensityColor(activity.averageHeartRate)} size={24} />
                                    </View>
                                    <View style={styles.activityInfo}>
                                        <Text style={styles.activityName}>{activity.activityName}</Text>
                                        <Text style={styles.activityMeta}>
                                            {activity.startTimeLocal.split('T')[0]} • {(activity.distance / 1000).toFixed(2)} km • {(activity.duration / 60).toFixed(0)} min
                                        </Text>
                                    </View>
                                    <ChevronRight color="#666" size={20} />
                                </TouchableOpacity>
                            ))
                        ) : (
                            <Text style={styles.noActivityText}>No activities found.</Text>
                        );
                    })()}
                </View>
            )}

            <View style={styles.calendarGrid}>
                {renderCalendarGrid()}
            </View>

            {!searchText && (
                <View style={styles.detailsSection}>
                    <Text style={styles.detailsTitle}>
                        Activities for {selectedDate.toDateString()}
                    </Text>

                    {(() => {
                        const selectedActivities = activities.filter(a => a.startTimeLocal.startsWith(selectedDateStr));

                        return selectedActivities.length > 0 ? (
                            selectedActivities.map(activity => (
                                <TouchableOpacity
                                    key={activity.activityId}
                                    style={styles.activityCard}
                                    onPress={() => navigation.navigate('ActivityDetail', { activity })}
                                >
                                    <View style={[styles.iconBox, { backgroundColor: getIntensityColor(activity.averageHeartRate) + '20' }]}>
                                        <Activity color={getIntensityColor(activity.averageHeartRate)} size={24} />
                                    </View>
                                    <View style={styles.activityInfo}>
                                        <Text style={styles.activityName}>{activity.activityName}</Text>
                                        <Text style={styles.activityMeta}>
                                            {activity.startTimeLocal.split('T')[0]} • {(activity.distance / 1000).toFixed(2)} km • {(activity.duration / 60).toFixed(0)} min
                                        </Text>
                                    </View>
                                    <ChevronRight color="#666" size={20} />
                                </TouchableOpacity>
                            ))
                        ) : (
                            <Text style={styles.noActivityText}>No activities recorded.</Text>
                        );
                    })()}
                </View>
            )}
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
        minHeight: 90, // Taller cells for boxes
        justifyContent: 'flex-start', // Align to top
        alignItems: 'center',
        borderWidth: 0.5,
        borderColor: '#222',
        paddingVertical: 4,
    },
    emptyCell: {
        backgroundColor: 'transparent',
        borderWidth: 0,
    },
    selectedDayCell: {
        backgroundColor: '#1A1A1A',
        borderColor: '#CCFF00',
        borderWidth: 1,
    },
    todayCell: {
        backgroundColor: '#222',
    },
    dayText: {
        color: '#888',
        fontSize: 12,
        marginBottom: 4,
    },
    selectedDayText: {
        color: 'white',
        fontWeight: 'bold',
    },
    eventContainer: {
        width: '100%',
        paddingHorizontal: 2,
        gap: 2,
    },
    eventBox: {
        width: '100%',
        paddingVertical: 4,
        paddingHorizontal: 2,
        borderRadius: 4,
        marginBottom: 2,
        borderWidth: 1, // Outlined style
    },
    eventName: {
        fontSize: 8,
        fontWeight: 'bold',
        textAlign: 'center',
        marginBottom: 1,
        opacity: 0.9,
    },
    eventText: {
        fontSize: 10, // Larger KM font
        fontWeight: '900',
        textAlign: 'center',
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
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        borderRadius: 8,
        paddingHorizontal: 12,
        marginBottom: 16,
        height: 40,
    },
    searchInput: {
        flex: 1,
        color: 'white',
        fontSize: 14,
    },
});

export default CalendarScreen;
