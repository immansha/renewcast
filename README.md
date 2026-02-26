# 🌱 RenewCast v4

## Autonomous Grid Dispatch System — Pathway Native

> Real-time renewable forecasting, RL-based backup dispatch, and regulatory-grounded AI advisories — inside a single streaming pipeline.

---

## 🚀 One-Line Pitch

RenewCast is a fully autonomous grid dispatch system where every new weather event triggers:

1. Online quantile forecast update
2. RL-based backup allocation
3. Compliance-gated dispatch decision
4. Regulatory-grounded AI advisory

All inside a single Pathway pipeline.

---

## 🏗 Architecture Overview

![Image](https://docs.aws.amazon.com/images/whitepapers/latest/build-modern-data-streaming-analytics-architectures/images/serverless-data-pipeline.png)

![Image](https://hpe-developer-portal.s3.amazonaws.com/uploads/media/2020/9/image7-1603902952832.png)

![Image](https://dz2cdn1.dzone.com/storage/temp/13912846-real-time-event-based-information-system-architect.png)

![Image](https://miro.medium.com/0%2Ak9vCsZDxVn27YWV0.jpg)

---

## 🔁 Real-Time Flow

```
Weather Event (30s)
        ↓
Pathway Sliding Window (6h per plant)
        ↓
River Quantile Model (P10/P50/P90)
        ↓
RL Dispatch Agent (PPO)
        ↓
Compliance Gate (RAG + Constraints)
        ↓
Dispatch Command + LLM Advisory
        ↓
Streamlit Live Dashboard
```

---

## 🧠 Core Technologies

| Component        | Technology                           |
| ---------------- | ------------------------------------ |
| Streaming Engine | Pathway                              |
| Online ML        | River (Quantile Regression)          |
| RL Agent         | Stable Baselines3 PPO                |
| RAG              | Pathway Document Store + GPT-4o-mini |
| UI               | Streamlit                            |
| Deployment       | Docker Compose                       |

---

## 📊 Live Demo Interface

![Image](https://miro.medium.com/v2/resize%3Afit%3A1400/1%2AR7LakSGt1Cb3_yC5DsuD1g.png)

![Image](https://res.cloudinary.com/graham-media-group/image/upload/f_auto/q_auto/c_scale%2Cw_640/v1/media/gmg/3KJMRS6HGVFPDBV7NMQ5HQZC2Q.jpg?_a=DAJHqpE+ZAAA)

![Image](https://miro.medium.com/v2/resize%3Afit%3A1400/1%2AEu7pM1p1C1WfFPb6KkOwow.png)

![Image](https://images.prismic.io/plotly-marketing-website-2/ed30f32d-cdc2-45d9-a4f4-2367142ec64a_Manufacturing1%2BManufacturing%2BSPC%2BDashboard.png?auto=format%2Ccompress)

### Dashboard Sections

* Per-plant forecast (P10/P50/P90)
* Live dispatch decisions
* Held compliance commands
* AI-generated regulatory advisory

---

## 🛡 Compliance Authority (Not Decorative AI)

Dispatch commands are gated before execution.

If:

* Ramp rate exceeded
* Must-run constraint violated

The command is **held**, not executed.

The AI advisory explains why.

---

## 📚 Live RAG Re-Index Demo

Drop new PDF into `/docs/` →
System re-indexes →
Next advisory references updated regulation.


