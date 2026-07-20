# 🔑 Google Gemini API Setup Guide

## ขั้นตอนการได้ Gemini API Key

### 1️⃣ ไปที่ Google AI Studio
📍 https://aistudio.google.com/app/apikey

### 2️⃣ Sign In ด้วย Google Account
- ใช้ Gmail account ของคุณ
- หรือสร้าง Google Account ใหม่

### 3️⃣ สร้าง API Key
1. คลิก **"Create API Key"** ปุ่มสีน้ำเงิน
2. เลือก **"Create API key in new project"**
3. Copy key ที่ได้

### 4️⃣ ใส่ API Key ลงใน .env

แก้ไฟล์ `.env`:

```env
GEMINI_API_KEY=your-gemini-api-key-here
```

ให้เปลี่ยน `your-gemini-api-key-here` เป็น API Key ที่ copy มา

ตัวอย่าง:
```env
GEMINI_API_KEY=AIzaSyDxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxX
```

---

## 💡 Gemini Models Available

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| **gemini-2.0-flash** ⭐ | ⚡ Very Fast | High | Low |
| gemini-1.5-flash | ⚡ Fast | Good | Low |
| gemini-1.5-pro | 🔥 Slower | Very High | Medium |
| gemini-pro | Moderate | Good | Low |

**เราใช้:** `gemini-2.0-flash` (เร็ว + ราคาถูก + คุณภาพดี)

---

## ✅ ตรวจสอบว่า Setup ถูก

```bash
# Activate venv
venv\Scripts\activate

# ติดตั้ง Gemini library
pip install google-generativeai==0.5.4

# ทดสอบ
python -c "import google.generativeai as genai; print('✅ Gemini API installed')"
```

---

## 🚀 ทดสอบ API Key

สร้างไฟล์ `test_gemini.py`:

```python
import google.generativeai as genai

# Configure
api_key = "your-api-key-here"  # แทน
genai.configure(api_key=api_key)

# Test
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content("Hello, test this API")

print("✅ Gemini API Works!")
print(f"Response: {response.text}")
```

รัน:
```bash
python test_gemini.py
```

---

## ⚠️ API Usage Limits (Free Tier)

- **Rate Limit:** 60 requests per minute
- **Daily Limit:** 1,500 requests per day
- **Free Tier:** Unlimited API calls (within limits)
- **Cost:** 0 - ฟรี! 🎉

---

## 🔒 Security Tips

### ❌ ห้าม:
```
GEMINI_API_KEY=AIzaSyD...  # ❌ Never commit to GitHub!
```

### ✅ ทำ:
```
# .env (local only)
GEMINI_API_KEY=AIzaSyD...

# .gitignore (protects .env)
.env
```

---

## 📝 Config ใน .env

Default settings:

```env
# Model
GEMINI_MODEL=gemini-2.0-flash

# Request settings
GEMINI_REQUEST_TIMEOUT=30
GEMINI_MAX_TOKENS=2048
GEMINI_TEMPERATURE=0.7

# Temperature อธิบาย:
# 0.0 = Deterministic (same output always)
# 0.5 = Balanced (good default)
# 1.0+ = Creative (varied outputs)
```

---

## 🔄 Comparison: Gemini vs Claude vs GPT-4

| Feature | Gemini 2.0 Flash | Claude 3.5 | GPT-4 |
|---------|-----------------|-----------|-------|
| Speed | ⚡⚡⚡ Very Fast | ⚡⚡ Fast | ⚡ Moderate |
| Quality | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Best | ⭐⭐⭐⭐ Excellent |
| Cost | 💰 Free/Cheap | 💰💰 Moderate | 💰💰💰 Expensive |
| Context | 1M tokens | 200K tokens | 128K tokens |

**สำหรับ Trading:** Gemini 2.0 Flash เป็นตัวเลือกที่ดี ✅

---

## ❓ Troubleshooting

### ❌ Error: "API key not set"
```
❌ GEMINI_API_KEY not found
```
→ ตรวจสอบ .env file มี key ไหม

### ❌ Error: "Invalid API key"
```
❌ API key invalid
```
→ Copy API key อีกครั้ง หรือสร้างใหม่

### ❌ Error: "Rate limit exceeded"
```
❌ Quota exceeded for quota metric
```
→ รอสักครู่ แล้วลองใหม่ (max 60 req/min)

---

## 📚 Resources

- **Gemini API Docs:** https://ai.google.dev/docs
- **Python SDK:** https://github.com/google/generative-ai-python
- **Free Tier:** https://ai.google.dev/free-tier
- **Pricing:** https://ai.google.dev/pricing

---

## ✅ Setup Checklist

- [ ] ไปที่ https://aistudio.google.com/app/apikey
- [ ] Sign in ด้วย Google Account
- [ ] สร้าง API Key
- [ ] Copy API Key
- [ ] แก้ไฟล์ .env ใส่ key
- [ ] ทดสอบด้วย `test_gemini.py`
- [ ] ลบไฟล์ `test_gemini.py`
- [ ] Push ไป GitHub (โดยไม่ push .env)

---

## 🎉 Done!

ตอนนี้ system พร้อมใช้ Gemini API แล้ว!

```bash
python src/main.py
```

สำเร็จ! 🚀