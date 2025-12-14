"""
Training Load Calculations
Based on knowledge_base.md formulas - Banister Impulse-Response Model

TSS Formula (HR-based for running):
    TSS = (Duration_sec × IF²) × 100 / 3600
    IF = Avg HR / LTHR

CTL/ATL/TSB (Exponential Moving Averages - Correct Banister Formula):
    k_ctl = 1 - e^(-1/42)  ≈ 0.0235
    k_atl = 1 - e^(-1/7)   ≈ 0.1331
    CTL = CTL_prev + (TSS - CTL_prev) × k_ctl  (Fitness, 42-day constant)
    ATL = ATL_prev + (TSS - ATL_prev) × k_atl  (Fatigue, 7-day constant)
    TSB = CTL - ATL                             (Form)
"""

import math
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional


def calculate_hrss(
    duration_seconds: float,
    avg_hr: int,
    lthr: int = 165,
    resting_hr: int = 45,
    gender: str = "male"
) -> float:
    """
    Calculate HR-based Training Stress Score (hrTSS/TRIMP)
    
    Uses Banister TRIMP formula adapted for HR zones:
    TRIMP = Duration × HRR × 0.64 × e^(1.92 × HRR)
    
    Where HRR = (Avg HR - Resting HR) / (Max HR - Resting HR)
    
    Then normalized to TSS scale where 1 hour at threshold = 100
    """
    if not duration_seconds or not avg_hr or not lthr:
        return 0.0
    
    # Use LTHR as proxy for threshold HR
    max_hr = int(lthr / 0.88)  # Approximate max HR from LTHR (88% of max)
    
    # Heart Rate Reserve ratio
    hrr = (avg_hr - resting_hr) / max((max_hr - resting_hr), 1)
    hrr = max(0, min(hrr, 1))  # Clamp to 0-1
    
    # Gender factor (women have slightly different lactate response)
    k = 1.92 if gender == "male" else 1.67
    
    # TRIMP calculation
    duration_minutes = duration_seconds / 60
    trimp = duration_minutes * hrr * 0.64 * math.exp(k * hrr)
    
    # Normalize to TSS scale (1 hour at threshold = 100)
    # Threshold TRIMP for 60 min ≈ 100
    threshold_trimp_60min = 60 * 0.88 * 0.64 * math.exp(k * 0.88)
    tss = (trimp / threshold_trimp_60min) * 100
    
    return round(tss, 1)


def calculate_tss_simple(
    duration_seconds: float,
    avg_hr: int,
    lthr: int = 165
) -> float:
    """
    Simplified TSS calculation using Intensity Factor
    
    IF = Avg HR / LTHR
    TSS = (Duration × IF²) × 100 / 3600
    """
    if not duration_seconds or not avg_hr or not lthr:
        return 0.0
    
    intensity_factor = avg_hr / lthr
    tss = (duration_seconds * (intensity_factor ** 2) * 100) / 3600
    
    return round(tss, 1)


def calculate_pmc(
    activities: List[Dict],
    days: int = 90,
    lthr: int = 165,
    resting_hr: int = 45,
    end_date: date = None  # Allow calculating PMC up to a specific date
) -> Dict:
    """
    Calculate Performance Management Chart data
    
    Returns:
        - ctl: current Chronic Training Load (Fitness)
        - atl: current Acute Training Load (Fatigue)
        - tsb: current Training Stress Balance (Form)
        - history: daily values for charting
        - weekly_tss: last 7 days total TSS
    """
    # Get date range - use provided end_date or today
    if end_date is None:
        end_date = datetime.now().date()
    elif hasattr(end_date, 'date'):
        end_date = end_date.date()
    start_date = end_date - timedelta(days=days + 42)  # Need 42 extra days for CTL initialization
    
    # Create daily TSS map from activities
    daily_tss: Dict[str, float] = {}
    
    for act in activities:
        # Parse activity date
        act_date = None
        if act.get('local_start_date'):
            act_date = act['local_start_date']
        elif act.get('start_time_local'):
            try:
                dt = act['start_time_local']
                if isinstance(dt, str):
                    dt = datetime.strptime(dt.split(' ')[0], '%Y-%m-%d')
                act_date = dt.date() if hasattr(dt, 'date') else dt
            except:
                continue
        
        if not act_date:
            continue
        
        date_key = str(act_date)
        
        # Calculate TSS for this activity
        duration = act.get('duration', 0) or 0
        avg_hr = act.get('average_hr', 0) or 0
        
        if duration > 0 and avg_hr > 0:
            tss = calculate_hrss(duration, avg_hr, lthr, resting_hr)
            daily_tss[date_key] = daily_tss.get(date_key, 0) + tss
    
    # Calculate CTL/ATL over time
    ctl = 0.0
    atl = 0.0
    history = []
    
    current = start_date
    while current <= end_date:
        date_key = str(current)
        today_tss = daily_tss.get(date_key, 0)
        
        # Exponential moving average update using correct Banister decay constants
        # CTL (Chronic Training Load): 42-day time constant
        # ATL (Acute Training Load): 7-day time constant
        # Formula: X_today = X_yesterday + (TSS_today - X_yesterday) * k
        # where k = 1 - e^(-1/time_constant)
        k_ctl = 1 - math.exp(-1/42)  # ≈ 0.0235 (not 1/42 = 0.0238)
        k_atl = 1 - math.exp(-1/7)   # ≈ 0.1331 (not 1/7 = 0.1428)
        
        ctl = ctl + (today_tss - ctl) * k_ctl
        atl = atl + (today_tss - atl) * k_atl
        tsb = ctl - atl
        
        # Only store data for the requested range
        if current > end_date - timedelta(days=days):
            history.append({
                'date': date_key,
                'tss': round(today_tss, 1),
                'ctl': round(ctl, 1),
                'atl': round(atl, 1),
                'tsb': round(tsb, 1)
            })
        
        current += timedelta(days=1)
    
    # Calculate weekly TSS
    week_ago = end_date - timedelta(days=7)
    weekly_tss = sum(
        daily_tss.get(str(week_ago + timedelta(days=i)), 0)
        for i in range(7)
    )
    
    # Get form status
    tsb = ctl - atl
    if tsb > 15:
        form_status = "FRESH"
        form_emoji = "🟢"
    elif tsb > 5:
        form_status = "OPTIMAL"
        form_emoji = "🟡"
    elif tsb > -10:
        form_status = "NEUTRAL"
        form_emoji = "⚪"
    elif tsb > -30:
        form_status = "TIRED"
        form_emoji = "🟠"
    else:
        form_status = "VERY_TIRED"
        form_emoji = "🔴"
    
    return {
        'ctl': round(ctl, 1),
        'atl': round(atl, 1),
        'tsb': round(tsb, 1),
        'form_status': form_status,
        'form_emoji': form_emoji,
        'weekly_tss': round(weekly_tss, 1),
        'history': history,  # Full history based on days parameter
        'is_overreaching': atl > ctl * 1.5
    }


def get_activity_tss(activity: Dict, lthr: int = 165, resting_hr: int = 45) -> float:
    """Get TSS for a single activity"""
    duration = activity.get('duration', 0) or 0
    avg_hr = activity.get('average_hr', 0) or 0
    
    if duration > 0 and avg_hr > 0:
        return calculate_hrss(duration, avg_hr, lthr, resting_hr)
    return 0.0


def get_recent_load_context(
    activities: List[Dict],
    activity_date: datetime,
    lthr: int = 165,
    resting_hr: int = 45
) -> Dict:
    """
    Get training load context for a specific activity date
    
    Returns CTL/ATL/TSB at the time of the activity, plus 7-day summary
    """
    # Filter activities before this date
    before_activities = []
    last_7_days_tss = 0
    
    for act in activities:
        act_date = None
        if act.get('local_start_date'):
            act_date = act['local_start_date']
        elif act.get('start_time_local'):
            try:
                dt = act['start_time_local']
                if isinstance(dt, str):
                    dt = datetime.strptime(dt.split(' ')[0], '%Y-%m-%d')
                act_date = dt.date() if hasattr(dt, 'date') else dt
            except:
                continue
        
        if not act_date:
            continue
        
        if isinstance(activity_date, str):
            activity_date = datetime.strptime(activity_date.split(' ')[0], '%Y-%m-%d').date()
        elif hasattr(activity_date, 'date'):
            activity_date = activity_date.date()
        
        if act_date < activity_date:
            before_activities.append(act)
            
            # Check if in last 7 days
            days_before = (activity_date - act_date).days
            if days_before <= 7:
                tss = get_activity_tss(act, lthr, resting_hr)
                last_7_days_tss += tss
    
    # Calculate PMC up to this date (not today!)
    pmc = calculate_pmc(before_activities, days=60, lthr=lthr, resting_hr=resting_hr, end_date=activity_date)
    
    return {
        'ctl_before': pmc['ctl'],
        'atl_before': pmc['atl'],
        'tsb_before': pmc['tsb'],
        'form_status': pmc['form_status'],
        'last_7_days_tss': round(last_7_days_tss, 1),
        'is_overreaching': pmc['is_overreaching']
    }


def get_weekly_breakdown(
    activities: List[Dict],
    weeks: int = 12,
    lthr: int = 165,
    resting_hr: int = 45
) -> Dict:
    """
    Get weekly breakdown by calendar weeks (Monday-Sunday)
    
    Returns:
        - current_week: TSS, distance, elevation for current calendar week
        - weekly_history: List of past weeks with all metrics
        - trend: Increasing/Decreasing/Stable
        - ctl_atl_history: Daily CTL/ATL for line chart
    """
    from datetime import datetime, timedelta
    import calendar
    
    today = datetime.now().date()
    
    # Find current week's Monday
    days_since_monday = today.weekday()  # 0=Monday
    current_week_start = today - timedelta(days=days_since_monday)
    
    # Build daily maps: TSS, distance, elevation
    daily_tss: Dict[str, float] = {}
    daily_distance: Dict[str, float] = {}
    daily_elevation: Dict[str, float] = {}
    
    for act in activities:
        act_date = None
        if act.get('local_start_date'):
            act_date = act['local_start_date']
        elif act.get('start_time_local'):
            try:
                dt = act['start_time_local']
                if isinstance(dt, str):
                    dt = datetime.strptime(dt.split(' ')[0], '%Y-%m-%d')
                act_date = dt.date() if hasattr(dt, 'date') else dt
            except:
                continue
        
        if not act_date:
            continue
        
        date_key = str(act_date)
        duration = act.get('duration', 0) or 0
        avg_hr = act.get('average_hr', 0) or 0
        distance = act.get('distance', 0) or 0
        elevation = act.get('elevation_gain', 0) or act.get('total_ascent', 0) or 0
        
        if duration > 0 and avg_hr > 0:
            tss = calculate_hrss(duration, avg_hr, lthr, resting_hr)
            daily_tss[date_key] = daily_tss.get(date_key, 0) + tss
        
        if distance > 0:
            daily_distance[date_key] = daily_distance.get(date_key, 0) + distance
        
        if elevation > 0:
            daily_elevation[date_key] = daily_elevation.get(date_key, 0) + elevation
    
    def format_week_label(week_start_date):
        """Format as 'Nov 2025, W2' (Strava style)"""
        month_abbr = calendar.month_abbr[week_start_date.month]
        year = week_start_date.year
        # Week of month: which week of that month is this?
        first_day_of_month = week_start_date.replace(day=1)
        week_of_month = ((week_start_date.day - 1) // 7) + 1
        return f"{month_abbr} {year}, W{week_of_month}"
    
    def get_week_metrics(week_start):
        """Calculate all metrics for a week"""
        tss = 0.0
        distance = 0.0
        elevation = 0.0
        for d in range(7):
            day = week_start + timedelta(days=d)
            date_key = str(day)
            tss += daily_tss.get(date_key, 0)
            distance += daily_distance.get(date_key, 0)
            elevation += daily_elevation.get(date_key, 0)
        return {
            'tss': round(tss, 1),
            'distance_km': round(distance / 1000, 1),
            'elevation_m': round(elevation, 0)
        }
    
    # Current week metrics
    current_metrics = get_week_metrics(current_week_start)
    days_in_current_week = min((today - current_week_start).days + 1, 7)
    
    # Past weeks
    weekly_history = []
    for w in range(weeks):
        week_start = current_week_start - timedelta(weeks=w+1)
        week_end = week_start + timedelta(days=6)
        metrics = get_week_metrics(week_start)
        weekly_history.append({
            'week_start': str(week_start),
            'week_end': str(week_end),
            'label': format_week_label(week_start),
            'week_number': week_start.isocalendar()[1],
            **metrics
        })
    
    # Reverse to chronological order
    weekly_history.reverse()
    
    # Averages
    completed_weeks = [w for w in weekly_history if w['tss'] > 0]
    avg_weekly_tss = sum(w['tss'] for w in completed_weeks) / len(completed_weeks) if completed_weeks else 0
    avg_weekly_distance = sum(w['distance_km'] for w in completed_weeks) / len(completed_weeks) if completed_weeks else 0
    avg_weekly_elevation = sum(w['elevation_m'] for w in completed_weeks) / len(completed_weeks) if completed_weeks else 0
    
    # Trend
    if len(weekly_history) >= 8:
        recent_4 = sum(w['tss'] for w in weekly_history[-4:]) / 4
        previous_4 = sum(w['tss'] for w in weekly_history[-8:-4]) / 4
        
        if recent_4 > previous_4 * 1.1:
            trend, trend_emoji = "INCREASING", "📈"
        elif recent_4 < previous_4 * 0.9:
            trend, trend_emoji = "DECREASING", "📉"
        else:
            trend, trend_emoji = "STABLE", "➡️"
    else:
        trend, trend_emoji = "INSUFFICIENT_DATA", "❓"
    
    # Projected for partial week
    if days_in_current_week > 0 and days_in_current_week < 7:
        factor = 7 / days_in_current_week
        projected_tss = current_metrics['tss'] * factor
        projected_distance = current_metrics['distance_km'] * factor
    else:
        projected_tss = current_metrics['tss']
        projected_distance = current_metrics['distance_km']
    
    # CTL/ATL daily history for line chart (last 90 days)
    ctl_atl_history = []
    pmc = calculate_pmc(activities, days=365, lthr=lthr, resting_hr=resting_hr)
    for h in pmc.get('history', []):
        ctl_atl_history.append({
            'date': h['date'],
            'ctl': h['ctl'],
            'atl': h['atl']
        })
    
    return {
        'current_week': {
            'start': str(current_week_start),
            'label': format_week_label(current_week_start),
            'tss': current_metrics['tss'],
            'distance_km': current_metrics['distance_km'],
            'elevation_m': current_metrics['elevation_m'],
            'days_completed': days_in_current_week,
            'projected_tss': round(projected_tss, 1),
            'projected_distance_km': round(projected_distance, 1)
        },
        'weekly_history': weekly_history,
        'avg_weekly_tss': round(avg_weekly_tss, 1),
        'avg_weekly_distance_km': round(avg_weekly_distance, 1),
        'avg_weekly_elevation_m': round(avg_weekly_elevation, 0),
        'trend': trend,
        'trend_emoji': trend_emoji,
        'weeks_analyzed': len(completed_weeks),
        'ctl_atl_history': ctl_atl_history
    }

