# AntiGravity Knowledge Base
> Extracted from 22 PDF documents covering running science, physiology, training algorithms, and app development.

---

## 1. 🧬 METABOLIC PHYSIOLOGY

### Lactate Kinetics
- **CCLS (Cell-to-Cell Lactate Shuttle)**: Lactate is NOT waste—it's a fuel and signaling molecule ("lactormone")
- **Producer cells**: Type IIb/IIx fibers (high PFK, LDH-A enzymes)
- **Consumer cells**: Type I fibers, myocardium, brain, liver/kidneys
- **mLOC (Mitochondrial Lactate Oxidation Complex)**: Lactate enters mitochondria directly via mMCT1

### VLaMax (Maximal Lactate Production Rate)
- Defines glycolytic capacity independent of VO2max
- **Lower VLaMax** = better fat oxidation, later lactate threshold
- **Higher VLaMax** = better sprint power, faster glycolytic energy
- **Target for marathoners**: < 0.3 mmol/L/s
- **Target for 1500m**: > 0.5 mmol/L/s

### Energy Systems
| System | Duration | Recovery | Training |
|--------|----------|----------|----------|
| ATP-PC (Alactic) | <10 sec | 1:12-1:20 work:rest | Short sprints, NMJ adaptation |
| Glycolytic | 10s-2min | Variable | Lactate tolerance |
| Oxidative | >2min | Continuous | Mitochondrial biogenesis |

---

## 2. 📊 TRAINING LOAD ALGORITHMS

### Normalized Power (NP) Formula
```
1. Smooth: 30-second moving average
2. Weight: Raise to 4th power
3. Average: Mean of weighted values
4. Root: Take 4th root
```
**Physiological basis**: 30s lag (VO2 kinetics) + 4th power (non-linear metabolic cost)

### Training Stress Score (TSS)
```
TSS = (Duration × NP × IF) / (FTP × 3600) × 100
IF = NP / FTP
```

### Performance Management Chart
| Metric | Calculation | Time Constant |
|--------|-------------|---------------|
| **CTL** (Fitness) | Exponential avg TSS | 42 days (τ₁) |
| **ATL** (Fatigue) | Exponential avg TSS | 7 days (τ₂) |
| **TSB** (Form) | CTL - ATL | Fresh > +10, Tired < -30 |

### Banister Impulse-Response Model
```
P(t) = k₁ × e^(-t/τ₁) - k₂ × e^(-t/τ₂)
```
Where: k₁=fitness gain, k₂=fatigue gain, τ₁=42d, τ₂=7d

---

## 3. 💓 HRV (Heart Rate Variability)

### Key Metrics
| Metric | Meaning | Good Sign | Bad Sign |
|--------|---------|-----------|----------|
| **RMSSD** | Parasympathetic activity | Higher values | Sudden drop |
| **SDNN** | Overall ANS variability | Normal range | Very low |
| **HF Power** | Vagal tone (0.15-0.4 Hz) | Higher | Suppressed |
| **LF Power** | Mixed sympathetic/vagal | Context-dependent | High chronic |
| **LF/HF Ratio** | Sympathovagal balance | ~1-2 at rest | >4 = stressed |

### Garmin HRV Status Interpretation
- **Balanced**: 7-day avg within personal baseline
- **Unbalanced (High)**: Training effect positive, adaptation occurring
- **Unbalanced (Low)**: Possible stress/under-recovery
- **Poor**: Multiple days of suppressed HRV, increase recovery

### Overtraining Detection
1. **Parasympathetic Saturation**: Chronically elevated HRV despite high load = plateau
2. **Sympathetic Overdrive**: Low HRV + elevated resting HR = non-functional overreaching
3. **Pattern**: Track 7-day rolling average, flag >15% deviation from baseline

---

## 4. 🏃 BIOMECHANICS

### Spring-Mass Model
- **Leg Stiffness (kleg)**: F_peak / ΔL_leg
- **Optimal stiffness**: Event-specific (higher for speed, lower for ultra)
- **Vertical Oscillation**: 8-12 cm optimal range

### Running Economy
- **Ground Contact Time (GCT)**: Elite < 200ms
- **Cadence**: 180+ spm reduces impact loading
- **Stride Length**: Natural optimization at given pace

### Injury Risk Factors
- Rapid training load increase (>10% weekly)
- Low cadence + high vertical oscillation
- Poor eccentric control (downhill running)

---

## 5. 📅 PERIODIZATION

### Phase Structure
| Phase | Duration | Focus | Intensity Distribution |
|-------|----------|-------|------------------------|
| **Base** | 8-12 weeks | Capillarization, aerobic enzymes | 80% Z2, 20% Z3 |
| **Build** | 4-8 weeks | Threshold, lactate clearance | 75% Z2, 15% Z4, 10% Z5 |
| **Specific** | 4-6 weeks | Race-pace, neuromuscular | 70% Z2, 20% race pace, 10% VO2max |
| **Taper** | 1-3 weeks | Fatigue shed, glycogen load | -40-60% volume, maintain intensity |

### Race Priority System
- **A Race**: Full taper (2-3 weeks)
- **B Race**: Mini-taper (3-5 days reduced load)
- **C Race**: Training day replacement (no taper)

### Mitochondrial-Capillary Paradox
- **HIIT**: +27% mitochondrial respiration (fast)
- **Endurance**: +5-10% greater capillary density
- **Solution**: Base phase for vasculature, Specific phase for function

---

## 6. 🔧 GARMIN FIT PROTOCOL

### File Structure
1. **Header** (12-14 bytes): Protocol version, data size, ".FIT" magic
2. **Data Records**: Sequence of Definition + Data messages
3. **CRC** (2 bytes): Validation checksum

### Key Message Types
| Message | Purpose | Key Fields |
|---------|---------|------------|
| `record` | Per-second stream | timestamp, heart_rate, speed, power, altitude, cadence |
| `lap` | Lap summaries | total_distance, avg_hr, avg_power, total_ascent |
| `session` | Activity summary | total_elapsed_time, total_timer_time, avg_speed |
| `sport` | Activity type | sport, sub_sport |
| `developer_data` | Third-party fields | Stryd, Core, ConnectIQ apps |

### Field Decoding Notes
- **position_lat/long**: semicircles → degrees: `val × (180 / 2^31)`
- **enhanced_speed**: m/s (higher precision than speed)
- **stance_time_balance**: % left/right (e.g., 50.1 = balanced)
- **perceived_effort**: Stored as val × 10 in unknown_193 field

---

## 7. 🎯 ADAPTIVE TRAINING PARAMETERS

### Genesis Vectors (Initialization)
1. **Goal Event**: Date, distance, terrain, priority (A/B/C)
2. **Current Fitness**: Recent activity history, VO2max estimate
3. **Availability**: Training days, time constraints
4. **Experience Level**: Beginner/Intermediate/Advanced
5. **Injury History**: Limiting factors

### Readiness Loop (Daily)
- **Objective**: Sleep quality, HRV, resting HR
- **Subjective**: RPE from previous day, mood, motivation (1-5 scale)
- **External**: Weather, travel stress, life events

### Feedback Mechanism (Post-Workout)
- **Session RPE** (0-10 scale): User perception vs objective load
- **Completion %**: Did they finish as prescribed?
- **Notes**: Free text for context

### Adjustment Logic
```
If (HRV < baseline - 15%) → reduce intensity by 10%
If (ATL > CTL × 1.5) → force recovery day
If (consecutive RPE > 7) → extend recovery
If (TSB < -30) → mandatory reload week
```

---

## 8. 📱 UI/UX BEST PRACTICES

### Dashboard Principles
1. **Primary Metric**: Single focus (e.g., today's workout)
2. **Secondary Context**: TSB, weekly load, streak
3. **Actionable**: Clear CTA ("Start Workout", "Log Recovery")
4. **Progressive Disclosure**: Details on tap, not overwhelm

### Chart Readability
- **X-axis**: `tickCount=6` for clean intervals
- **Labels**: Minute format (`10'`, `20'`)
- **Font**: 11px, #888 for visibility
- **Grid**: Subtle (#222), not distracting

### Color Coding
| Context | Color | Usage |
|---------|-------|-------|
| Primary CTA | #CCFF00 | Buttons, highlights |
| Heart Rate | #FF3333 | HR zone, effort |
| Pace/Speed | #00CCFF | Velocity metrics |
| Power | #FFFF00 | Wattage |
| Elevation | #CC00FF | Altitude, climb |
| Success | #33FF33 | Completed, positive |
| Warning | #FF9900 | Caution, attention |

---

## 9. 🧠 DECISION PARAMETERS

### When to Push vs. Rest
| Signal | Action |
|--------|--------|
| HRV high + low ATL | Green light: intensity session |
| HRV low + high ATL | Recovery: easy or off |
| Chronic low HRV | Doctor check, forced rest week |
| TSB > +15 | Undertrained, increase load |
| TSB < -30 | Overreached, deload |

### Workout Selection Logic
```
IF goal_race_type == "marathon":
    prioritize = ["long_run", "threshold", "tempo"]
    avoid = ["pure_sprints", "track_repeats"]
ELIF goal_race_type == "5k":
    prioritize = ["VO2max_intervals", "threshold", "strides"]
    avoid = ["4hr_long_runs"]
```

### Taper Recommendations
| Event Distance | Taper Length | Volume Reduction |
|----------------|--------------|------------------|
| 5K-10K | 5-7 days | 30-40% |
| Half Marathon | 10-14 days | 40-50% |
| Marathon | 14-21 days | 50-60% |
| Ultra | 21-28 days | 60-70% |

---

## 10. 🔑 CRITICAL FORMULAS

### Running Power (Estimated)
```
Power_run ≈ (body_mass × grade_factor × speed) + (0.5 × air_density × CdA × speed³)
```

### Pace Zones from Threshold
| Zone | % Threshold | Purpose |
|------|-------------|---------|
| Z1 | <75% | Recovery |
| Z2 | 75-85% | Aerobic base |
| Z3 | 85-95% | Tempo |
| Z4 | 95-105% | Threshold |
| Z5 | 105-120% | VO2max |
| Z6 | >120% | Anaerobic |

### Race Time Prediction (Riegel Formula)
```
T2 = T1 × (D2/D1)^1.06
```
Where: T1=known time, D1=known distance, D2=target distance

---

*This knowledge base is extracted from AntiGravity's PDF library. Use for algorithm design, feature decisions, and training prescription logic.*
