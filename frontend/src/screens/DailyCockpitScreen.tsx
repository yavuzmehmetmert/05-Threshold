import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, useWindowDimensions, TouchableOpacity, Alert, Animated, Easing } from 'react-native';
import { useDashboardStore } from '../store/useDashboardStore';
import { Battery, Zap, Activity, TrendingUp, AlertTriangle, ChevronRight, Play, RefreshCw, Moon, Sun, Heart, MessageCircle } from 'lucide-react-native';
import { useNavigation } from '@react-navigation/native';
import { HocaChatModal, HocaFAB } from '../components/HocaChatModal';

const MetricCard = ({ title, value, subtext, icon: Icon, color, style }: any) => (
    <View style={[styles.card, style]}>
        <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>{title}</Text>
            <Icon size={16} color={color} />
        </View>
        <Text style={[styles.cardValue, { color }]}>{value}</Text>
        <Text style={styles.cardSubtext}>{subtext}</Text>
    </View>
);

// Training Analytics Carousel Component
const TrainingAnalyticsCarousel = ({ weeklyData, navigation }: any) => {
    const [activeSlide, setActiveSlide] = React.useState(0);
    const [showInfoPopup, setShowInfoPopup] = React.useState(false);
    const [weekOffset, setWeekOffset] = React.useState(0);
    const slides = ['summary', 'distance', 'tss', 'fitness'];

    const nextSlide = () => setActiveSlide(prev => (prev + 1) % slides.length);
    const prevSlide = () => setActiveSlide(prev => (prev - 1 + slides.length) % slides.length);

    return (
        <View style={styles.card}>
            {/* Info Popup Overlay - Content based on activeSlide */}
            {showInfoPopup && (
                <TouchableOpacity
                    style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.95)', zIndex: 100, padding: 16, borderRadius: 12 }}
                    activeOpacity={1}
                    onPress={() => setShowInfoPopup(false)}
                >
                    {activeSlide === 1 ? (
                        <>
                            <Text style={{ color: '#00CCFF', fontSize: 14, fontWeight: 'bold', marginBottom: 10 }}>📊 Weekly Distance</Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                Her bar bir haftanın <Text style={{ color: '#00CCFF' }}>toplam koşu mesafesini</Text> (km) gösterir.
                            </Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#99CC00' }}>↑ değeri</Text> = O haftanın toplam tırmanış (elevation gain) miktarı.
                            </Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#00CCFF' }}>Mavi barlar</Text> = Son 2 hafta (güncel dönem).
                            </Text>
                            <Text style={{ color: '#666', fontSize: 10, marginTop: 10 }}>
                                💡 ◀ ▶ oklarıyla geçmiş haftalara bakabilirsin.
                            </Text>
                        </>
                    ) : activeSlide === 0 ? (
                        <>
                            <Text style={{ color: '#CCFF00', fontSize: 14, fontWeight: 'bold', marginBottom: 10 }}>📊 Weekly Summary</Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#CCFF00' }}>KM</Text> - Bu hafta koşulan toplam mesafe.
                            </Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#FF9900' }}>TSS</Text> (Training Stress Score) - Antrenman yükünü ölçer. Süre ve yoğunluğun birleşimidir.
                            </Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#00CCFF' }}>Projected</Text> - Mevcut gidişata göre hafta sonu tahmini toplam mesafe.
                            </Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#999' }}>Trend</Text> - Son 4 haftaya göre yük değişimi.
                            </Text>
                        </>
                    ) : activeSlide === 2 ? (
                        <>
                            <Text style={{ color: '#FF9900', fontSize: 14, fontWeight: 'bold', marginBottom: 10 }}>📊 Weekly TSS Load</Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                Her bar bir haftanın <Text style={{ color: '#FF9900' }}>toplam TSS</Text> (Training Stress Score) değerini gösterir.
                            </Text>
                            <Text style={{ color: '#AAA', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#FFF' }}>TSS = Süre × Yoğunluk</Text>. Ne kadar yorulursan o kadar artar.
                            </Text>
                            <Text style={{ color: '#666', fontSize: 10, marginTop: 10 }}>
                                💡 Düzenli gelişim için TSS'in haftadan haftaya kontrollü artması gerekir.
                            </Text>
                        </>
                    ) : activeSlide === 3 ? (
                        <>
                            <Text style={{ color: '#CCFF00', fontSize: 14, fontWeight: 'bold', marginBottom: 10 }}>📊 How to Read PMC Chart</Text>
                            <Text style={{ color: '#888', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#00CCFF' }}>CTL (Fitness)</Text> = 42-day training load average. Higher = more fit.
                            </Text>
                            <Text style={{ color: '#888', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#FF6600' }}>ATL (Fatigue)</Text> = 7-day training load average. Higher = more tired.
                            </Text>
                            <Text style={{ color: '#888', fontSize: 11, lineHeight: 18, marginBottom: 8 }}>
                                <Text style={{ color: '#CCFF00' }}>TSB (Form)</Text> = CTL - ATL. Positive = fresh, negative = fatigued.
                            </Text>
                            <Text style={{ color: '#666', fontSize: 10, marginTop: 8 }}>
                                🟢 +15: Peak performance{'\n'}
                                🟡 +5 to +15: Fresh, ready to race{'\n'}
                                ⚪ -10 to +5: Neutral{'\n'}
                                🟠 -25 to -10: Building fitness{'\n'}
                                🔴 Below -25: Overreaching risk
                            </Text>
                        </>
                    ) : (
                        <Text style={{ color: '#888', fontSize: 11 }}>Bilgi mevcut değil.</Text>
                    )}
                    <Text style={{ color: '#444', fontSize: 9, textAlign: 'center', marginTop: 12 }}>tap to close</Text>
                </TouchableOpacity>
            )
            }

            {/* Header with title, info button, and navigation dots */}
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Text style={styles.cardTitle}>
                        {activeSlide === 0 ? 'This Week' : activeSlide === 1 ? 'Weekly Distance' : activeSlide === 2 ? 'Weekly TSS Load' : 'Fitness vs Fatigue'}
                    </Text>
                    {activeSlide === 3 && (
                        <TouchableOpacity onPress={() => setShowInfoPopup(true)}>
                            <View style={{ width: 18, height: 18, borderRadius: 9, backgroundColor: '#333', justifyContent: 'center', alignItems: 'center' }}>
                                <Text style={{ color: '#888', fontSize: 11, fontWeight: 'bold' }}>i</Text>
                            </View>
                        </TouchableOpacity>
                    )}
                </View>
                <View style={{ flexDirection: 'row', gap: 6 }}>
                    {slides.map((_, idx) => (
                        <TouchableOpacity key={idx} onPress={() => setActiveSlide(idx)}>
                            <View style={{
                                width: 8, height: 8, borderRadius: 4,
                                backgroundColor: idx === activeSlide ? '#CCFF00' : '#444'
                            }} />
                        </TouchableOpacity>
                    ))}
                </View>
            </View>

            {/* Slide Content */}
            <TouchableOpacity activeOpacity={1} onPress={nextSlide}>
                {/* Slide 0: Current Week Summary */}
                {activeSlide === 0 && (
                    <View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 }}>
                            <Text style={{ color: '#888', fontSize: 11 }}>{weeklyData.current_week.label} ({weeklyData.current_week.days_completed}/7 days)</Text>
                            <TouchableOpacity onPress={() => setShowInfoPopup(!showInfoPopup)} style={{ padding: 4 }}>
                                <Text style={{ color: '#888', fontSize: 12 }}>ⓘ</Text>
                            </TouchableOpacity>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginBottom: 16 }}>
                            <View style={{ alignItems: 'center' }}>
                                <Text style={{ color: '#CCFF00', fontSize: 32, fontWeight: 'bold' }}>{weeklyData.current_week.distance_km}</Text>
                                <Text style={{ color: '#666', fontSize: 11 }}>km</Text>
                            </View>
                            <TouchableOpacity onPress={() => setActiveSlide(2)} style={{ alignItems: 'center' }}>
                                <Text style={{ color: '#FF9900', fontSize: 32, fontWeight: 'bold' }}>{weeklyData.current_week.tss}</Text>
                                <Text style={{ color: '#666', fontSize: 11 }}>TSS 👆</Text>
                            </TouchableOpacity>
                        </View>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', padding: 10, backgroundColor: '#0A0A0A', borderRadius: 8 }}>
                            <Text style={{ color: '#666', fontSize: 10 }}>Projected: {weeklyData.current_week.projected_distance_km} km</Text>
                            <Text style={{ color: '#666', fontSize: 10 }}>Avg: {weeklyData.avg_weekly_distance_km} km/wk</Text>
                        </View>
                        <Text style={{ color: '#888', fontSize: 11, marginTop: 12, textAlign: 'center' }}>{weeklyData.trend_emoji} {weeklyData.trend}</Text>
                    </View>
                )}

                {/* Slide 1: Weekly Distance Chart */}
                {activeSlide === 1 && (() => {
                    const history = weeklyData.weekly_history || [];
                    const weeksToShow = 8;
                    const totalWeeks = history.length;

                    // Use separate offset for distance chart (stored in weekOffset for now, share with PMC)
                    const endIdx = Math.min(totalWeeks, totalWeeks - weekOffset + weeksToShow);
                    const startIdx = Math.max(0, endIdx - weeksToShow);
                    const visibleWeeks = history.slice(startIdx, endIdx);

                    const canGoBackDist = startIdx > 0;
                    const canGoForwardDist = endIdx < totalWeeks;

                    const maxKm = Math.max(...visibleWeeks.map((w: any) => w.distance_km), 1);

                    return (
                        <View>
                            {/* Navigation Header with Info */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                <TouchableOpacity
                                    onPress={() => {
                                        if (canGoBackDist) {
                                            setWeekOffset(prev => prev + weeksToShow);
                                        }
                                        // Always consume touch - don't bubble
                                    }}
                                    style={{ padding: 8, opacity: canGoBackDist ? 1 : 0.3 }}
                                >
                                    <Text style={{ color: '#00CCFF', fontSize: 18, fontWeight: 'bold' }}>◀</Text>
                                </TouchableOpacity>
                                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                    <Text style={{ color: '#666', fontSize: 10 }}>Weekly Distance</Text>
                                    <TouchableOpacity onPress={() => setShowInfoPopup(!showInfoPopup)} style={{ marginLeft: 6 }}>
                                        <Text style={{ color: '#888', fontSize: 12 }}>ⓘ</Text>
                                    </TouchableOpacity>
                                </View>
                                <TouchableOpacity
                                    onPress={() => {
                                        if (canGoForwardDist) {
                                            setWeekOffset(prev => Math.max(0, prev - weeksToShow));
                                        }
                                        // Always consume touch - don't bubble
                                    }}
                                    style={{ padding: 8, opacity: canGoForwardDist ? 1 : 0.3 }}
                                >
                                    <Text style={{ color: '#00CCFF', fontSize: 18, fontWeight: 'bold' }}>▶</Text>
                                </TouchableOpacity>
                            </View>

                            {/* Chart */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: 100, marginBottom: 8 }}>
                                {visibleWeeks.map((week: any, idx: number) => {
                                    const height = Math.max((week.distance_km / maxKm) * 55, 6);
                                    const isRecent = idx >= visibleWeeks.length - 2;
                                    const elevation = week.elevation_m || 0;
                                    // Extract week label: "Nov 2025, W2" -> "Nov\nW2"
                                    const labelParts = week.label.split(', ');
                                    const monthShort = labelParts[0].substring(0, 3);
                                    const weekNum = labelParts[1] || 'W?';
                                    return (
                                        <TouchableOpacity
                                            key={week.week_start}
                                            style={{ alignItems: 'center', flex: 1, marginHorizontal: 1 }}
                                            activeOpacity={0.7}
                                            onPress={() => {
                                                const start = new Date(week.week_start);
                                                const end = new Date(start);
                                                end.setDate(end.getDate() + 6);
                                                const endDateStr = end.toISOString().split('T')[0];

                                                navigation.navigate('WeekDetail', {
                                                    startDate: week.week_start,
                                                    endDate: endDateStr,
                                                    weekLabel: week.label
                                                });
                                            }}
                                        >
                                            {/* Values stacked vertically */}
                                            <View style={{ alignItems: 'center', marginBottom: 3 }}>
                                                <Text style={{ color: '#00CCFF', fontSize: 9, fontWeight: 'bold' }}>{week.distance_km}</Text>
                                                {elevation > 0 && (
                                                    <Text style={{ color: '#99CC00', fontSize: 7 }}>↑{Math.round(elevation)}</Text>
                                                )}
                                            </View>
                                            {/* Bar */}
                                            <View style={{ backgroundColor: isRecent ? '#00CCFF' : '#444', width: '80%', height, borderRadius: 3 }} />
                                            {/* Label: Month + Week */}
                                            <Text style={{ color: '#555', fontSize: 7, marginTop: 2 }}>{monthShort}</Text>
                                            <Text style={{ color: '#666', fontSize: 6 }}>{weekNum}</Text>
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>

                            {/* Footer */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                                <Text style={{ color: '#666', fontSize: 10 }}>Avg: {weeklyData.avg_weekly_distance_km} km/week</Text>
                                <Text style={{ color: '#888', fontSize: 10 }}>{weeklyData.trend_emoji} {weeklyData.trend}</Text>
                            </View>
                        </View>
                    );
                })()}
            </TouchableOpacity>

            {/* Slide 2: Weekly TSS Chart */}
            <TouchableOpacity activeOpacity={1} onPress={nextSlide}>
                {activeSlide === 2 && (() => {
                    const history = weeklyData.weekly_history || [];
                    const weeksToShow = 8;
                    const totalWeeks = history.length;
                    const endIdx = Math.min(totalWeeks, totalWeeks - weekOffset + weeksToShow);
                    const startIdx = Math.max(0, endIdx - weeksToShow);
                    const visibleWeeks = history.slice(startIdx, endIdx);
                    const canGoBack = startIdx > 0;
                    const canGoForward = endIdx < totalWeeks;
                    const maxTss = Math.max(...visibleWeeks.map((w: any) => w.tss), 1);

                    return (
                        <View>
                            {/* Navigation */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                <TouchableOpacity onPress={() => canGoBack && setWeekOffset(prev => prev + weeksToShow)} style={{ padding: 8, opacity: canGoBack ? 1 : 0.3 }}>
                                    <Text style={{ color: '#FF9900', fontSize: 18, fontWeight: 'bold' }}>◀</Text>
                                </TouchableOpacity>
                                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                    <Text style={{ color: '#666', fontSize: 10 }}>Weekly TSS</Text>
                                    <TouchableOpacity onPress={() => setShowInfoPopup(!showInfoPopup)} style={{ marginLeft: 6 }}>
                                        <Text style={{ color: '#888', fontSize: 12 }}>ⓘ</Text>
                                    </TouchableOpacity>
                                </View>
                                <TouchableOpacity onPress={() => canGoForward && setWeekOffset(prev => Math.max(0, prev - weeksToShow))} style={{ padding: 8, opacity: canGoForward ? 1 : 0.3 }}>
                                    <Text style={{ color: '#FF9900', fontSize: 18, fontWeight: 'bold' }}>▶</Text>
                                </TouchableOpacity>
                            </View>

                            {/* Chart */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: 100, marginBottom: 8 }}>
                                {visibleWeeks.map((week: any, idx: number) => {
                                    const height = Math.max((week.tss / maxTss) * 55, 6);
                                    const isRecent = idx >= visibleWeeks.length - 2;
                                    const labelParts = week.label.split(', ');
                                    return (
                                        <TouchableOpacity
                                            key={week.week_start}
                                            style={{ alignItems: 'center', flex: 1, marginHorizontal: 1 }}
                                            activeOpacity={0.7}
                                            onPress={() => {
                                                const start = new Date(week.week_start);
                                                const end = new Date(start);
                                                end.setDate(end.getDate() + 6);
                                                navigation.navigate('WeekDetail', {
                                                    startDate: week.week_start,
                                                    endDate: end.toISOString().split('T')[0],
                                                    weekLabel: week.label
                                                });
                                            }}
                                        >
                                            <View style={{ alignItems: 'center', marginBottom: 3 }}>
                                                <Text style={{ color: '#FF9900', fontSize: 9, fontWeight: 'bold' }}>{week.tss}</Text>
                                            </View>
                                            <View style={{ backgroundColor: isRecent ? '#FF9900' : '#444', width: '80%', height, borderRadius: 3 }} />
                                            <Text style={{ color: '#555', fontSize: 7, marginTop: 2 }}>{labelParts[0].substring(0, 3)}</Text>
                                            <Text style={{ color: '#666', fontSize: 6 }}>{labelParts[1] || 'W?'}</Text>
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                                <Text style={{ color: '#666', fontSize: 10 }}>Avg: {weeklyData.avg_weekly_tss} TSS/week</Text>
                            </View>
                        </View>
                    );
                })()}
            </TouchableOpacity >

            {/* Slide 3: Fitness vs Fatigue (replaces Slide 2) */}
            {
                activeSlide === 3 && weeklyData.ctl_atl_history && weeklyData.ctl_atl_history.length > 10 && (() => {
                    const history = weeklyData.ctl_atl_history;
                    const totalDays = history.length;
                    const totalWeeks = Math.floor(totalDays / 7);

                    // Dynamically show available weeks (up to 8, min 4)
                    const weeksToShow = Math.min(8, Math.max(4, totalWeeks));

                    console.log('PMC DEBUG: totalDays=', totalDays, 'totalWeeks=', totalWeeks, 'weeksToShow=', weeksToShow, 'weekOffset=', weekOffset);

                    // Now using calendar week grouping instead of index-based weeks

                    // Build weekly data points - GROUP BY ACTUAL CALENDAR WEEKS (Mon-Sun)
                    const weeklyPoints: any[] = [];
                    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

                    // Group daily history by calendar week (Monday start)
                    const weekMap: { [mondayKey: string]: { ctl: number, atl: number, date: string, monday: Date } } = {};

                    for (const day of history) {
                        const date = new Date(day.date);
                        // Find Monday of this week
                        const dayOfWeek = date.getDay(); // 0=Sun, 1=Mon, ...
                        const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
                        const monday = new Date(date);
                        monday.setDate(date.getDate() - daysToMonday);
                        const mondayKey = monday.toISOString().split('T')[0];

                        // Store the LAST day's CTL/ATL values for each week (Sunday's values)
                        weekMap[mondayKey] = {
                            ctl: day.ctl,
                            atl: day.atl,
                            date: day.date,
                            monday: monday
                        };
                    }

                    // Convert to sorted array
                    const allWeeks = Object.keys(weekMap)
                        .sort()
                        .map(key => ({
                            mondayKey: key,
                            ...weekMap[key],
                            label: `${monthNames[weekMap[key].monday.getMonth()]} ${weekMap[key].monday.getDate()}`,
                            weekStartDate: key,
                            weekEndDate: weekMap[key].date
                        }));

                    // Apply pagination
                    const totalWeeksAvailable = allWeeks.length;
                    const endIndex = totalWeeksAvailable - weekOffset;
                    const startIndex = Math.max(0, endIndex - weeksToShow);
                    const visibleWeeks = allWeeks.slice(startIndex, endIndex);

                    // Check navigation
                    const canGoBack = startIndex > 0;
                    const canGoForward = weekOffset > 0;

                    console.log('PMC CALENDAR WEEKS: total=', totalWeeksAvailable, 'showing=', startIndex, '-', endIndex);

                    weeklyPoints.push(...visibleWeeks);

                    const currentPoint = history[totalDays - 1];
                    const currentCtl = Math.round(currentPoint?.ctl || 0);
                    const currentAtl = Math.round(currentPoint?.atl || 0);
                    const currentTsb = Math.round((currentCtl - currentAtl) * 10) / 10;
                    const maxVal = Math.max(...weeklyPoints.map((h: any) => Math.max(h.ctl, h.atl)), 50);
                    const chartHeight = 100;

                    // Form status
                    let formStatus = '', formColor = '#888';
                    if (currentTsb > 15) { formStatus = '🟢 Peak Form'; formColor = '#CCFF00'; }
                    else if (currentTsb > 5) { formStatus = '🟡 Fresh'; formColor = '#FFCC00'; }
                    else if (currentTsb > -10) { formStatus = '⚪ Neutral'; formColor = '#888'; }
                    else if (currentTsb > -25) { formStatus = '🟠 Building'; formColor = '#FF9900'; }
                    else { formStatus = '🔴 Overreaching'; formColor = '#FF3333'; }

                    return (
                        <View>
                            {/* Current Values */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                                <View>
                                    <Text style={{ color: '#00CCFF', fontSize: 28, fontWeight: 'bold' }}>{currentCtl}</Text>
                                    <Text style={{ color: '#666', fontSize: 10 }}>Fitness</Text>
                                </View>
                                <View style={{ alignItems: 'center' }}>
                                    <Text style={{ color: formColor, fontSize: 22, fontWeight: 'bold' }}>
                                        {currentTsb > 0 ? '+' : ''}{currentTsb}
                                    </Text>
                                    <Text style={{ color: formColor, fontSize: 9 }}>{formStatus}</Text>
                                </View>
                                <View style={{ alignItems: 'flex-end' }}>
                                    <Text style={{ color: '#FF6600', fontSize: 28, fontWeight: 'bold' }}>{currentAtl}</Text>
                                    <Text style={{ color: '#666', fontSize: 10 }}>Fatigue</Text>
                                </View>
                            </View>

                            {/* Navigation Header */}
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                <TouchableOpacity
                                    onPress={() => {
                                        console.log('LEFT ARROW PRESSED, canGoBack:', canGoBack, 'weekOffset:', weekOffset, 'startIndex:', startIndex);
                                        if (canGoBack) {
                                            setWeekOffset(weekOffset + 8);
                                        }
                                    }}
                                    style={{ padding: 12, opacity: canGoBack ? 1 : 0.3 }}
                                >
                                    <Text style={{ color: '#CCFF00', fontSize: 20, fontWeight: 'bold' }}>◀</Text>
                                </TouchableOpacity>
                                <Text style={{ color: '#666', fontSize: 10 }}>Weekly CTL/ATL (offset: {weekOffset})</Text>
                                <TouchableOpacity
                                    onPress={() => {
                                        console.log('RIGHT ARROW PRESSED, canGoForward:', canGoForward, 'weekOffset:', weekOffset);
                                        if (canGoForward) {
                                            setWeekOffset(Math.max(0, weekOffset - 8));
                                        }
                                    }}
                                    style={{ padding: 12, opacity: canGoForward ? 1 : 0.3 }}
                                >
                                    <Text style={{ color: '#CCFF00', fontSize: 20, fontWeight: 'bold' }}>▶</Text>
                                </TouchableOpacity>
                            </View>

                            {/* Weekly Bar Chart - Touchable Bars */}
                            <View style={{ height: chartHeight, flexDirection: 'row', alignItems: 'flex-end', marginBottom: 4 }}>
                                {weeklyPoints.map((point: any, idx: number) => {
                                    const ctlVal = Math.round(point.ctl);
                                    const atlVal = Math.round(point.atl);
                                    const ctlHeight = Math.max((point.ctl / maxVal) * (chartHeight - 25), 5);
                                    const atlHeight = Math.max((point.atl / maxVal) * (chartHeight - 25), 5);
                                    return (
                                        <TouchableOpacity
                                            key={point.date}
                                            style={{ flex: 1, alignItems: 'center', height: chartHeight, justifyContent: 'flex-end' }}
                                            onPress={() => {
                                                // Navigate to WeekDetailScreen
                                                navigation.navigate('WeekDetail', {
                                                    startDate: point.weekStartDate,
                                                    endDate: point.weekEndDate,
                                                    weekLabel: point.label
                                                });
                                            }}
                                            activeOpacity={0.7}
                                        >
                                            {/* Values on top */}
                                            <View style={{ position: 'absolute', top: 0, alignItems: 'center' }}>
                                                <Text style={{ color: '#00CCFF', fontSize: 8, fontWeight: 'bold' }}>{ctlVal}</Text>
                                                <Text style={{ color: '#FF6600', fontSize: 7 }}>{atlVal}</Text>
                                            </View>
                                            {/* CTL bar */}
                                            <View style={{
                                                position: 'absolute', bottom: 18, width: '80%', height: ctlHeight,
                                                backgroundColor: 'rgba(0, 204, 255, 0.4)', borderTopLeftRadius: 3, borderTopRightRadius: 3,
                                            }} />
                                            {/* ATL bar */}
                                            <View style={{
                                                position: 'absolute', bottom: 18, width: '50%', height: atlHeight,
                                                backgroundColor: 'rgba(255, 102, 0, 0.8)', borderTopLeftRadius: 2, borderTopRightRadius: 2,
                                            }} />
                                            {/* Week label */}
                                            <Text style={{ position: 'absolute', bottom: 0, color: '#555', fontSize: 8 }}>{point.label}</Text>
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>

                            {/* Legend */}
                            <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 16, marginTop: 6 }}>
                                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                                    <View style={{ width: 12, height: 8, backgroundColor: 'rgba(0, 204, 255, 0.5)', borderRadius: 2 }} />
                                    <Text style={{ color: '#666', fontSize: 9 }}>CTL (Fitness)</Text>
                                </View>
                                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                                    <View style={{ width: 12, height: 8, backgroundColor: 'rgba(255, 102, 0, 0.7)', borderRadius: 2 }} />
                                    <Text style={{ color: '#666', fontSize: 9 }}>ATL (Fatigue)</Text>
                                </View>
                            </View>
                        </View>
                    );
                })()
            }

            {/* Tap hint */}
            <Text style={{ color: '#444', fontSize: 9, textAlign: 'center', marginTop: 12 }}>
                {activeSlide === 2 ? 'use arrows to navigate weeks' : 'tap to switch'}
            </Text>
        </View >
    );
};

const DailyCockpitScreen = () => {
    const navigation = useNavigation<any>();
    const store = useDashboardStore();
    const userProfile = useDashboardStore(state => state.userProfile);
    const activities = useDashboardStore(state => state.activities);
    const setActivities = useDashboardStore(state => state.setActivities);
    const { width } = useWindowDimensions();
    const isDesktop = width > 768;

    // Sync state and animation
    const [syncing, setSyncing] = React.useState(false);
    const [showHocaChat, setShowHocaChat] = React.useState(false);
    const spinValue = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        if (syncing) {
            Animated.loop(
                Animated.timing(spinValue, {
                    toValue: 1,
                    duration: 1000,
                    easing: Easing.linear,
                    useNativeDriver: true,
                })
            ).start();
        } else {
            spinValue.setValue(0);
        }
    }, [syncing]);

    const spin = spinValue.interpolate({
        inputRange: [0, 1],
        outputRange: ['0deg', '360deg']
    });

    const handleSync = async () => {
        if (syncing) return;
        setSyncing(true);
        try {
            const response = await fetch('http://localhost:8000/ingestion/sync/incremental', {
                method: 'POST'
            });
            const result = await response.json();
            console.log('Sync result:', result);

            // Refresh dashboard data
            fetchWeeklyData();
            if (activities.length === 0 || result.new_activities > 0) {
                const res = await fetch('http://localhost:8000/ingestion/activities?limit=3');
                const data = await res.json();
                setActivities(data);
            }
        } catch (error) {
            console.error('Sync failed:', error);
            Alert.alert('Sync Failed', 'Could not sync data from Garmin');
        } finally {
            setSyncing(false);
        }
    };

    useEffect(() => {
        // Fetch activities if empty
        if (activities.length === 0) {
            fetch('http://localhost:8000/ingestion/activities?limit=3')
                .then(res => {
                    if (!res.ok) throw new Error('Failed to fetch activities');
                    return res.json();
                })
                .then(data => setActivities(data))
                .catch(err => {
                    console.error('Activity Fetch Error:', err);
                    // Optionally set empty activities to avoid crash if data structure is expected
                    setActivities([]);
                });
        }

        // Fetch weekly training load data
        fetchWeeklyData();
    }, []);

    const [weeklyData, setWeeklyData] = React.useState<{
        current_week: {
            start: string;
            label: string;
            tss: number;
            distance_km: number;
            elevation_m: number;
            days_completed: number;
            projected_tss: number;
            projected_distance_km: number;
        };
        weekly_history: Array<{
            week_start: string;
            week_number: number;
            label: string;
            tss: number;
            distance_km: number;
            elevation_m: number;
        }>;
        avg_weekly_tss: number;
        avg_weekly_distance_km: number;
        trend: string;
        trend_emoji: string;
        ctl_atl_history: Array<{ date: string; ctl: number; atl: number }>;
    } | null>(null);

    const fetchWeeklyData = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/training-load/weekly');
            const data = await response.json();
            setWeeklyData(data);
        } catch (error) {
            console.error('Failed to fetch weekly data:', error);
        }
    };

    // Fetch real TSB/Form and calculate Readiness
    const fetchTrainingLoad = async () => {
        try {
            const response = await fetch('http://localhost:8000/ingestion/training-load');
            const data = await response.json();

            // Get current TSB (Form) from the API
            const currentTsb = data.tsb || 0;
            store.setTsb(Math.round(currentTsb));

            // Calculate Readiness Score
            // Readiness = Base(50) + TSB_contribution + Sleep_contribution + HRV_contribution - Stress_contribution
            // TSB: +25 for high positive, -25 for deep negative
            // Sleep: +10 for good sleep (>7h), -10 for poor (<5h)
            // HRV: +10 for balanced, -10 for poor
            // Stress: -0.2 per stress point above 30

            // This will be refined after dailyOverview is set
            const tsbContribution = Math.max(-25, Math.min(25, currentTsb * 2));
            let readiness = 50 + tsbContribution;

            // Clamp to 0-100
            readiness = Math.max(0, Math.min(100, Math.round(readiness)));
            store.setReadinessScore(readiness);

        } catch (error) {
            console.error('Failed to fetch training load:', error);
        }
    };

    // Daily Overview State (for morning widget)
    const [dailyOverview, setDailyOverview] = React.useState<{
        sleep: { duration_hours: number | null; score: number | null } | null;
        hrv: { last_night_avg: number | null; status: string | null } | null;
        stress: { avg: number | null } | null;
        resting_hr: number | null;
        last_sync: string | null;
    } | null>(null);

    const fetchDailyOverview = async () => {
        try {
            // Get yesterday's date
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            const dateStr = yesterday.toISOString().split('T')[0];

            // Fetch all data in parallel using existing endpoints
            const [sleepRes, hrvRes, stressRes, profileRes] = await Promise.all([
                fetch(`http://localhost:8000/ingestion/sleep/${dateStr}`),
                fetch(`http://localhost:8000/ingestion/hrv/${dateStr}`),
                fetch(`http://localhost:8000/ingestion/stress/${dateStr}`),
                fetch('http://localhost:8000/ingestion/profile/latest')
            ]);

            const sleepData = await sleepRes.json();
            const hrvData = await hrvRes.json();
            const stressData = await stressRes.json();
            const profileData = await profileRes.json();

            // Parse the nested API response structures
            // Sleep API returns: { dailySleepDTO: { dailySleepDTO: {...}, avgOvernightHrv, hrvStatus, restingHeartRate } }
            const outerSleepDTO = sleepData?.dailySleepDTO;
            const innerSleepDTO = outerSleepDTO?.dailySleepDTO;

            setDailyOverview({
                sleep: innerSleepDTO?.sleepTimeSeconds ? {
                    duration_hours: Math.round((innerSleepDTO.sleepTimeSeconds / 3600) * 10) / 10,
                    score: innerSleepDTO.sleepScores?.overall?.value || null
                } : null,
                hrv: outerSleepDTO?.avgOvernightHrv ? {
                    last_night_avg: Math.round(outerSleepDTO.avgOvernightHrv),
                    status: outerSleepDTO.hrvStatus || null
                } : null,
                stress: stressData?.avgStress ? {
                    avg: stressData.avgStress
                } : null,
                resting_hr: outerSleepDTO?.restingHeartRate || profileData?.restingHr || null,
                last_sync: profileData?.date || null
            });
        } catch (error) {
            console.error('Failed to fetch daily overview:', error);
        }
    };

    // Time-based greeting
    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour >= 5 && hour < 12) return { text: 'Good Morning', emoji: '☀️' };
        if (hour >= 12 && hour < 17) return { text: 'Good Afternoon', emoji: '🌤️' };
        if (hour >= 17 && hour < 21) return { text: 'Good Evening', emoji: '🌅' };
        return { text: 'Good Night', emoji: '🌙' };
    };

    useEffect(() => {
        fetchDailyOverview();
    }, []);

    // Fetch real TSB and calculate Readiness
    useEffect(() => {
        fetchTrainingLoad();
    }, []);

    // Update readiness after dailyOverview is set
    React.useEffect(() => {
        if (dailyOverview) {
            let readiness = 50;

            // TSB contribution (from store)
            const tsbContribution = Math.max(-25, Math.min(25, store.tsb * 2));
            readiness += tsbContribution;

            // Sleep contribution (+10 for >7h, +5 for >6h, -5 for <5h)
            const sleepHours = dailyOverview.sleep?.duration_hours || 7;
            if (sleepHours >= 7) readiness += 10;
            else if (sleepHours >= 6) readiness += 5;
            else if (sleepHours < 5) readiness -= 5;

            // HRV contribution (+10 for BALANCED, -5 for LOW)
            const hrvStatus = dailyOverview.hrv?.status?.toUpperCase() || 'BALANCED';
            if (hrvStatus === 'BALANCED') readiness += 10;
            else if (hrvStatus === 'LOW') readiness -= 5;

            // Stress contribution (-1 for every 10 points above 30)
            const stressAvg = dailyOverview.stress?.avg || 30;
            if (stressAvg > 30) readiness -= Math.floor((stressAvg - 30) / 10);

            // Clamp to 0-100
            readiness = Math.max(0, Math.min(100, Math.round(readiness)));
            store.setReadinessScore(readiness);
        }
    }, [dailyOverview, store.tsb]);

    const getReadinessColor = (score: number) => {
        if (score >= 80) return '#CCFF00'; // Green
        if (score >= 50) return '#FFCC00'; // Yellow
        return '#FF3333'; // Red
    };

    const readinessColor = getReadinessColor(store.readinessScore);

    return (
        <View style={styles.container}>
            <ScrollView contentContainerStyle={styles.scrollContent}>
                <View style={styles.content}>

                    {/* Header */}
                    <View style={styles.header}>
                        <View>
                            <Text style={styles.headerLabel}>TODAY</Text>
                            <Text style={styles.headerTitle}>Daily Cockpit</Text>
                        </View>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                            <TouchableOpacity
                                onPress={handleSync}
                                disabled={syncing}
                                style={[styles.circle, { borderColor: syncing ? '#CCFF00' : readinessColor, backgroundColor: syncing ? 'rgba(204, 255, 0, 0.1)' : 'rgba(255, 255, 255, 0.05)' }]}
                            >
                                <Animated.View style={{ transform: [{ rotate: spin }] }}>
                                    <RefreshCw size={20} color={syncing ? '#CCFF00' : '#888'} />
                                </Animated.View>
                            </TouchableOpacity>
                            <View style={[styles.circle, { borderColor: readinessColor }]}>
                                <Activity size={20} color={readinessColor} />
                            </View>
                        </View>
                    </View>

                    {/* Adaptation Banner */}
                    {store.adaptation?.active && (
                        <View style={styles.banner}>
                            <AlertTriangle size={24} color="#FF3333" />
                            <View style={styles.bannerContent}>
                                <Text style={styles.bannerTitle}>Plan Adapted</Text>
                                <Text style={styles.bannerText}>{store.adaptation.reason}</Text>
                                <Text style={styles.bannerSubtext}>{store.adaptation.change}</Text>
                            </View>
                        </View>
                    )}

                    {/* Responsive Grid */}
                    <View style={[styles.gridContainer, isDesktop && styles.gridContainerDesktop]}>

                        {/* Left Column: Metrics */}
                        <View style={[styles.column, isDesktop && styles.columnLeft]}>
                            {/* Key Metrics Row */}
                            <View style={styles.row}>
                                <MetricCard
                                    title="Readiness"
                                    value={store.readinessScore}
                                    subtext="Prime State"
                                    icon={Activity}
                                    color={readinessColor}
                                    style={{ flex: 1 }}
                                />
                                <View style={{ width: 12 }} />
                                <MetricCard
                                    title="Form (TSB)"
                                    value={store.tsb > 0 ? `+${store.tsb}` : store.tsb}
                                    subtext="Peaking"
                                    icon={TrendingUp}
                                    color="#00CCFF"
                                    style={{ flex: 1 }}
                                />
                            </View>

                            {/* Morning Widget - Greeting + Daily Stats */}
                            <View style={styles.card}>
                                {/* Greeting Header */}
                                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 12 }}>
                                    <Text style={{ fontSize: 16, marginRight: 8 }}>{getGreeting().emoji}</Text>
                                    <View>
                                        <Text style={{ color: '#888', fontSize: 11 }}>{getGreeting().text}</Text>
                                        <Text style={{ color: '#FFF', fontSize: 18, fontWeight: 'bold' }}>
                                            Runner
                                        </Text>
                                    </View>
                                </View>

                                {/* Yesterday's Stats Grid */}
                                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
                                    {/* Sleep */}
                                    <View style={{ flex: 1, minWidth: '45%', backgroundColor: '#1A1A1A', borderRadius: 8, padding: 10 }}>
                                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                                            <Moon size={14} color="#8B5CF6" />
                                            <Text style={{ color: '#888', fontSize: 10, marginLeft: 6 }}>Sleep</Text>
                                        </View>
                                        <Text style={{ color: '#8B5CF6', fontSize: 20, fontWeight: 'bold' }}>
                                            {dailyOverview?.sleep?.duration_hours || '--'}h
                                        </Text>
                                        {dailyOverview?.sleep?.score && (
                                            <Text style={{ color: '#666', fontSize: 10 }}>Score: {dailyOverview.sleep.score}</Text>
                                        )}
                                    </View>

                                    {/* HRV */}
                                    <View style={{ flex: 1, minWidth: '45%', backgroundColor: '#1A1A1A', borderRadius: 8, padding: 10 }}>
                                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                                            <Activity size={14} color="#22C55E" />
                                            <Text style={{ color: '#888', fontSize: 10, marginLeft: 6 }}>HRV</Text>
                                        </View>
                                        <Text style={{ color: '#22C55E', fontSize: 20, fontWeight: 'bold' }}>
                                            {dailyOverview?.hrv?.last_night_avg || '--'}ms
                                        </Text>
                                        {dailyOverview?.hrv?.status && (
                                            <Text style={{ color: '#666', fontSize: 10 }}>{dailyOverview.hrv.status}</Text>
                                        )}
                                    </View>

                                    {/* Resting HR */}
                                    <View style={{ flex: 1, minWidth: '45%', backgroundColor: '#1A1A1A', borderRadius: 8, padding: 10 }}>
                                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                                            <Heart size={14} color="#EF4444" />
                                            <Text style={{ color: '#888', fontSize: 10, marginLeft: 6 }}>Resting HR</Text>
                                        </View>
                                        <Text style={{ color: '#EF4444', fontSize: 20, fontWeight: 'bold' }}>
                                            {dailyOverview?.resting_hr || '--'}bpm
                                        </Text>
                                    </View>

                                    {/* Stress */}
                                    <View style={{ flex: 1, minWidth: '45%', backgroundColor: '#1A1A1A', borderRadius: 8, padding: 10 }}>
                                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                                            <Zap size={14} color="#F59E0B" />
                                            <Text style={{ color: '#888', fontSize: 10, marginLeft: 6 }}>Stress</Text>
                                        </View>
                                        <Text style={{ color: '#F59E0B', fontSize: 20, fontWeight: 'bold' }}>
                                            {dailyOverview?.stress?.avg || '--'}
                                        </Text>
                                        <Text style={{ color: '#666', fontSize: 10 }}>avg</Text>
                                    </View>
                                </View>

                                {/* Last Sync */}
                                {dailyOverview?.last_sync && (
                                    <View style={{ marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#222' }}>
                                        <Text style={{ color: '#555', fontSize: 10, textAlign: 'center' }}>
                                            Last Sync: {dailyOverview.last_sync}
                                        </Text>
                                    </View>
                                )}
                            </View>

                            {/* Weekly Training Load - Carousel */}
                            {weeklyData && (
                                <TrainingAnalyticsCarousel weeklyData={weeklyData} navigation={navigation} />
                            )}
                        </View>

                        {/* Right Column: Workout */}
                        <View style={[styles.column, isDesktop && styles.columnRight]}>
                            <View style={styles.section}>
                                <Text style={styles.sectionTitle}>Today's Mission</Text>
                                {store.todayWorkout ? (
                                    <View style={[styles.workoutCard, { flex: 1 }]}>
                                        <View style={styles.workoutHeader}>
                                            <Text style={styles.workoutType}>{store.todayWorkout.type}</Text>
                                            <Text style={styles.workoutDuration}>{store.todayWorkout.duration}</Text>
                                        </View>
                                        <Text style={styles.workoutIntensity}>{store.todayWorkout.intensity}</Text>
                                        <Text style={styles.workoutDesc}>{store.todayWorkout.description}</Text>

                                        <View style={{ flex: 1 }} />

                                        <TouchableOpacity style={styles.button} onPress={() => navigation.navigate('LiveActivity')}>
                                            <Play size={20} color="#050505" />
                                            <Text style={styles.buttonText}>Start Workout</Text>
                                        </TouchableOpacity>
                                    </View>
                                ) : (
                                    <View style={styles.card}>
                                        <Text style={styles.textWhite}>Rest Day</Text>
                                    </View>
                                )}
                            </View>
                        </View>

                    </View>

                    {/* Recent Activities */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Recent Activities</Text>
                        {activities.slice(0, 3).map(activity => (
                            <TouchableOpacity
                                key={activity.activityId}
                                style={styles.activityCard}
                                onPress={() => navigation.navigate('ActivityDetail', { activity })}
                            >
                                <View style={[styles.iconBox, { backgroundColor: '#CCFF0020' }]}>
                                    <Activity color="#CCFF00" size={20} />
                                </View>
                                <View style={{ flex: 1 }}>
                                    <Text style={styles.activityName}>{activity.activityName}</Text>
                                    <Text style={styles.activityMeta}>
                                        {new Date(activity.startTimeLocal).toLocaleDateString()} • {(activity.distance / 1000).toFixed(1)} km
                                    </Text>
                                </View>
                                <ChevronRight color="#666" size={20} />
                            </TouchableOpacity>
                        ))}
                        {activities.length === 0 && (
                            <Text style={{ color: '#666', fontStyle: 'italic' }}>No recent activities found.</Text>
                        )}
                    </View>
                </View>
            </ScrollView>

            {/* Hoca AI Coach FAB */}
            <HocaFAB onPress={() => setShowHocaChat(true)} />

            {/* Hoca Chat Modal */}
            <HocaChatModal
                visible={showHocaChat}
                onClose={() => setShowHocaChat(false)}
            />
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#050505',
        width: '100%',
        overflow: 'hidden',
    },
    scrollContent: {
        flexGrow: 1,
        width: '100%',
    },
    content: {
        width: '100%',
        padding: 20,
        gap: 20,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10,
    },
    headerLabel: {
        color: '#999',
        fontSize: 12,
        fontWeight: '600',
        marginBottom: 4,
    },
    headerTitle: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
    },
    circle: {
        width: 40,
        height: 40,
        borderRadius: 20,
        borderWidth: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
    gridContainer: {
        flexDirection: 'column',
        gap: 20,
    },
    gridContainerDesktop: {
        flexDirection: 'row',
        alignItems: 'stretch',
    },
    column: {
        flex: 1,
        gap: 20,
    },
    columnLeft: {
        flex: 1,
    },
    columnRight: {
        flex: 1,
    },
    row: {
        flexDirection: 'row',
        gap: 12,
    },
    card: {
        backgroundColor: '#111',
        borderRadius: 12,
        padding: 16,
        borderWidth: 1,
        borderColor: '#333',
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    cardTitle: {
        color: '#999',
        fontSize: 12,
    },
    cardValue: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 4,
    },
    cardSubtext: {
        color: '#666',
        fontSize: 12,
    },
    banner: {
        backgroundColor: '#331100',
        borderColor: '#FF3333',
        borderWidth: 1,
        borderRadius: 12,
        padding: 12,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    bannerContent: {
        flex: 1,
    },
    bannerTitle: {
        color: '#FF3333',
        fontWeight: 'bold',
        marginBottom: 4,
    },
    bannerText: {
        color: 'white',
        fontSize: 14,
        marginBottom: 2,
    },
    bannerSubtext: {
        color: '#999',
        fontSize: 12,
    },
    batteryRow: {
        flexDirection: 'row',
        alignItems: 'baseline',
        gap: 8,
        marginBottom: 12,
    },
    progressBar: {
        height: 4,
        backgroundColor: '#333',
        borderRadius: 2,
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
    },
    section: {
        flex: 1,
        gap: 12,
    },
    sectionTitle: {
        color: 'white',
        fontSize: 18,
        fontWeight: 'bold',
    },
    workoutCard: {
        backgroundColor: '#111',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#333',
        overflow: 'hidden',
    },
    workoutHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        padding: 16,
        paddingBottom: 8,
    },
    workoutType: {
        color: '#CCFF00',
        fontWeight: 'bold',
    },
    workoutDuration: {
        color: 'white',
    },
    workoutIntensity: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
        paddingHorizontal: 16,
        marginBottom: 8,
    },
    workoutDesc: {
        color: '#999',
        paddingHorizontal: 16,
        marginBottom: 16,
    },
    button: {
        backgroundColor: '#CCFF00',
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 16,
        gap: 8,
    },
    buttonText: {
        color: '#050505',
        fontWeight: 'bold',
        fontSize: 16,
    },
    textWhite: {
        color: 'white',
    },
    activityCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#111',
        padding: 16,
        borderRadius: 12,
        marginBottom: 10,
        gap: 12,
    },
    iconBox: {
        width: 36,
        height: 36,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
    },
    activityName: {
        color: 'white',
        fontSize: 14,
        fontWeight: '600',
    },
    activityMeta: {
        color: '#888',
        fontSize: 12,
        marginTop: 2,
    },
});

export default DailyCockpitScreen;
