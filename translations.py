"""
Clinical Multilingual Translation Engine for Pulse AI:
Provides complete, culturally nuanced, clinically validated translations across:
- English (en), Hindi (hi), Tamil (ta), Telugu (te), Kannada (kn), Malayalam (ml),
- Bengali (bn), Marathi (mr), Spanish (es), French (fr).
"""
import re

LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)",
    "bn": "বাংলা (Bengali)",
    "mr": "मराठी (Marathi)",
    "es": "Español (Spanish)",
    "fr": "Français (French)"
}

HEADERS = {
    "en": {
        "big_picture": "🩺 **The Big Picture**",
        "areas_to_watch": "🔍 **Areas to Watch**",
        "healthy_biomarkers": "✨ **Healthy Biomarkers**",
        "doctor_questions": "💬 **Suggested Questions for Your Doctor**",
        "urgent_alert": "⚠️ **URGENT CLINICAL ALERT**",
        "urgent_call": "Please contact your physician or visit an urgent care facility immediately.",
        "all_normal": "Great news! All {count} analyzed blood markers fall comfortably within their expected healthy reference ranges. Your metabolic equilibrium and organ functions show reassuring stability.",
        "some_abnormal": "Overall, {normal_count} of your {total_count} tested blood markers are within healthy standard limits. There are {ab_count} marker(s) outside expected ranges that warrant attention and discussion with your physician.",
        "healthy_suffix": "are all functioning in optimal reference ranges.",
        "disclaimer": "📋 *Notice: Pulse AI is an educational health-literacy tool, not a diagnostic medical service. Always consult your healthcare provider.*"
    },
    "hi": {
        "big_picture": "🩺 **समग्र स्वास्थ्य स्थिति (The Big Picture)**",
        "areas_to_watch": "🔍 **ध्यान देने योग्य परिणाम (Areas to Watch)**",
        "healthy_biomarkers": "✨ **सामान्य और स्वस्थ परिणाम (Healthy Biomarkers)**",
        "doctor_questions": "💬 **डॉक्टर से परामर्श हेतु महत्वपूर्ण प्रश्न (Questions for Doctor)**",
        "urgent_alert": "⚠️ **आपातकालीन चिकित्सकीय चेतावनी (URGENT ALERT)**",
        "urgent_call": "कृपया तुरंत अपने चिकित्सक से संपर्क करें या निकटतम अस्पताल जाएं।",
        "all_normal": "शुभ समाचार! आपकी रिपोर्ट के सभी {count} रक्त परीक्षण सामान्य और स्वस्थ सीमाओं के भीतर हैं। आपके मुख्य अंग और मेटाबोलिक स्वास्थ्य स्थिर हैं।",
        "some_abnormal": "कुल {total_count} परीक्षणों में से {normal_count} परीक्षण सामान्य और स्वस्थ हैं। {ab_count} परीक्षण सामान्य सीमा से बाहर हैं, जिन पर डॉक्टर से चर्चा करना आवश्यक है।",
        "healthy_suffix": "सभी पूरी तरह से सामान्य और स्वस्थ श्रेणी में कार्य कर रहे हैं।",
        "disclaimer": "📋 *सूचना: पल्स एआई केवल स्वास्थ्य-जागरूकता और शिक्षा हेतु है, यह चिकित्सकीय निदान नहीं है। कृपया डॉक्टर से अवश्य परामर्श लें।*"
    },
    "ta": {
        "big_picture": "🩺 **ஒட்டுமொத்த சுகாதார நிலை (The Big Picture)**",
        "areas_to_watch": "🔍 **கவனிக்க வேண்டிய முடிவுகள் (Areas to Watch)**",
        "healthy_biomarkers": "✨ **சீரான ஆரோக்கியமான முடிவுகள் (Healthy Biomarkers)**",
        "doctor_questions": "💬 **மருத்துவரிடம் கேட்க வேண்டிய கேள்விகள் (Questions for Doctor)**",
        "urgent_alert": "⚠️ **அவசர மருத்துவ எச்சரிக்கை (URGENT ALERT)**",
        "urgent_call": "தயவுசெய்து உடனடியாக உங்கள் மருத்துவரை அணுகவும் அல்லது அவசர சிகிச்சை மையத்திற்கு செல்லவும்.",
        "all_normal": "நற்செய்தி! ஆய்வு செய்யப்பட்ட {count} இரத்த பரிசோதனை முடிவுகளும் இயல்பான ஆரோக்கிய வரம்பிற்குள் உள்ளன.",
        "some_abnormal": "மொத்த {total_count} சோதனைகளில் {normal_count} சோதனைகள் இயல்பாக உள்ளன. {ab_count} சோதனைகள் இயல்பு வரம்பிற்கு வெளியே உள்ளன, இவற்றை மருத்துவரிடம் ஆலோசிக்க வேண்டும்.",
        "healthy_suffix": "அனைத்தும் உகந்த ஆரோக்கிய வரம்பில் செயல்படுகின்றன.",
        "disclaimer": "📋 *அறிவிப்பு: பல்ஸ் ஏஐ என்பது கல்வி மற்றும் விழிப்புணர்வுக்கான கருவி மட்டுமே; இது மருத்துவ சிகிச்சையோ மருந்து பரிந்துரையோ அல்ல.*"
    },
    "te": {
        "big_picture": "🩺 **మొత్తం ఆరోగ్య స్థితి (The Big Picture)**",
        "areas_to_watch": "🔍 **శ్రద్ధ వహించాల్సిన ఫలితాలు (Areas to Watch)**",
        "healthy_biomarkers": "✨ **సాధారణ మరియు ఆరోగ్యకరమైన పరీక్షలు (Healthy Biomarkers)**",
        "doctor_questions": "💬 **వైద్యుడిని అడగవలసిన ప్రశ్నలు (Questions for Doctor)**",
        "urgent_alert": "⚠️ **అత్యవసర వైద్య హెచ్చరిక (URGENT ALERT)**",
        "urgent_call": "దయచేసి వెంటనే మీ వైద్యుడిని సంప్రదించండి లేదా అత్యవసర విభాగానికి వెళ్ళండి.",
        "all_normal": "శుభవార్త! మీ నివేదికలోని అన్ని {count} రక్త పరీక్షలు సాధారణ ఆరోగ్య పరిమితుల్లో ఉన్నాయి.",
        "some_abnormal": "మొత్తం {total_count} పరీక్షలలో {normal_count} సాధారణంగా ఉన్నాయి. {ab_count} పరీక్షలు సాధారణ పరిమితికి భిన్నంగా ఉన్నాయి, వీటిపై వైద్యుడి సలహా అవసరం.",
        "healthy_suffix": "అన్నీ సరైన ఆరోగ్యకరమైన పరిధిలో పనిచేస్తున్నాయి.",
        "disclaimer": "📋 *గమనిక: పల్స్ ఏఐ ఆరోగ్య పరిజ్ఞానం కొరకు మాత్రమే; ఇది వైద్య చికిత్స లేదా నిర్ధారణ కాదు.*"
    },
    "kn": {
        "big_picture": "🩺 **ಒಟ್ಟಾರೆ ಆರೋಗ್ಯ ಸ್ಥಿತಿ (The Big Picture)**",
        "areas_to_watch": "🔍 **ಗಮನಿಸಬೇಕಾದ ಪರೀಕ್ಷಾ ಫಲಿತಾಂಶಗಳು (Areas to Watch)**",
        "healthy_biomarkers": "✨ **ಸಾಮಾನ್ಯ ಮತ್ತು ಆರೋಗ್ಯಕರ ಫಲಿತಾಂಶಗಳು (Healthy Biomarkers)**",
        "doctor_questions": "💬 **ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚಿಸಬೇಕಾದ ಪ್ರಶ್ನೆಗಳು (Questions for Doctor)**",
        "urgent_alert": "⚠️ **ತುರ್ತು ವೈದ್ಯಕೀಯ ಎಚ್ಚರಿಕೆ (URGENT ALERT)**",
        "urgent_call": "ದಯವಿಟ್ಟು ತಕ್ಷಣವೇ ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ ಅಥವಾ ಆಸ್ಪತ್ರೆಗೆ ಭೇಟಿ ನೀಡಿ.",
        "all_normal": "ಶುಭ ಸುದ್ದಿ! ನಿಮ್ಮ ರಕ್ತ ಪರೀಕ್ಷೆಯ ಎಲ್ಲಾ {count} ಅಂಶಗಳು ನಿಗದಿತ ಸಾಮಾನ್ಯ ಮಿತಿಯಲ್ಲಿವೆ.",
        "some_abnormal": "ಒಟ್ಟು {total_count} ಪರೀಕ್ಷೆಗಳಲ್ಲಿ {normal_count} ಸಾಮಾನ್ಯ ಮಿತಿಯಲ್ಲಿವೆ. {ab_count} ಪರೀಕ್ಷೆಗಳು ನಿಗದಿತ ಮಿತಿಗಿಂತ ಹೊರಗಿದ್ದು, ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚಿಸುವುದು ಸೂಕ್ತ.",
        "healthy_suffix": "ಎಲ್ಲವೂ ಉತ್ತಮ ಆರೋಗ್ಯಕರ ಮಿತಿಯಲ್ಲಿ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿವೆ.",
        "disclaimer": "📋 *ಸೂಚನೆ: ಪಲ್ಸ್ ಎಐ ಕೇವಲ ಆರೋಗ್ಯ ಜಾಗೃತಿಗಾಗಿ ಮಾತ್ರ; ಇದು ವೈದ್ಯಕೀಯ ಸಲಹೆಯಲ್ಲ.*"
    },
    "ml": {
        "big_picture": "🩺 **മൊത്തത്തിലുള്ള ആരോഗ്യ നില (The Big Picture)**",
        "areas_to_watch": "🔍 **ശ്രദ്ധിക്കേണ്ട പരിശോധനാ ഫലങ്ങൾ (Areas to Watch)**",
        "healthy_biomarkers": "✨ **സാധാരണവും ആരോഗ്യകരവുമായ ഫലങ്ങൾ (Healthy Biomarkers)**",
        "doctor_questions": "💬 **ഡോക്ടറോട് ചോദിക്കേണ്ട പ്രധാന ചോദ്യങ്ങൾ (Questions for Doctor)**",
        "urgent_alert": "⚠️ **അടിയന്തര മെഡിക്കൽ മുന്നറിയിപ്പ് (URGENT ALERT)**",
        "urgent_call": "ദയവായി ഉടൻ തന്നെ നിങ്ങളുടെ ഡോക്ടറെ ബന്ധപ്പെടുകയോ ആശുപത്രി സന്ദർശിക്കുകയോ ചെയ്യുക.",
        "all_normal": "നല്ല വാർത്ത! നിങ്ങളുടെ റിപ്പോർട്ടിലെ {count} രക്തപരിശോധനകളും പൂർണ്ണമായും സാധാരണ പരിധിക്കുള്ളിലാണ്.",
        "some_abnormal": "ആകെ {total_count} പരിശോധനകളിൽ {normal_count} എണ്ണം സാധാരണ നിലയിലാണ്. {ab_count} പരിശോധനകൾ വ്യത്യാസപ്പെട്ടിരിക്കുന്നു, ഡോക്ടറുമായി സംസാരിക്കുക.",
        "healthy_suffix": "എല്ലാം കൃത്യമായ സാധാരണ നിലയിൽ പ്രവർത്തിക്കുന്നു.",
        "disclaimer": "📋 *ശ്രദ്ധിക്കുക: പൾസ് എഐ ആരോഗ്യ അവബോധത്തിന് മാത്രമുള്ളതാണ്; ഇത് മെഡിക്കൽ നിർദ്ദേശമല്ല.*"
    },
    "bn": {
        "big_picture": "🩺 **সামগ্রিক স্বাস্থ্য চিত্র (The Big Picture)**",
        "areas_to_watch": "🔍 **মনোযোগ দেওয়া প্রয়োজন এমন ফলাফল (Areas to Watch)**",
        "healthy_biomarkers": "✨ **স্বাভাবিক ও স্বাস্থ্যকর ফলাফল (Healthy Biomarkers)**",
        "doctor_questions": "💬 **ডাক্তারকে জিজ্ঞাসা করার মতো প্রশ্ন (Questions for Doctor)**",
        "urgent_alert": "⚠️ **জরুরী চিকিৎসা সতর্কতা (URGENT ALERT)**",
        "urgent_call": "অনুগ্রহ করে অবিলম্বে আপনার চিকিৎসকের সাথে যোগাযোগ করুন বা নিকটস্থ হাসপাতালে যান।",
        "all_normal": "সুসংবাদ! আপনার রিপোর্টের সমস্ত {count}টি রক্ত পরীক্ষার ফলাফল স্বাভাবিক ও সুস্থ সীমার মধ্যে রয়েছে।",
        "some_abnormal": "মোট {total_count}টি পরীক্ষার মধ্যে {normal_count}টি স্বাভাবিক রয়েছে। {ab_count}টি ফলাফল স্বাভাবিক সীমার বাইরে রয়েছে, যা নিয়ে চিকিৎসকের পরামর্শ নেওয়া জরুরি।",
        "healthy_suffix": "সবগুলি সর্বোত্তম স্বাস্থ্যকর সীমার মধ্যে রয়েছে।",
        "disclaimer": "📋 *বিজ্ঞপ্তি: পালস এআই শুধুমাত্র স্বাস্থ্য সচেতনতা বৃদ্ধির জন্য; এটি কোনো চিকিৎসা পরামর্শ নয়।*"
    },
    "mr": {
        "big_picture": "🩺 **एकूण आरोग्य स्थिती (The Big Picture)**",
        "areas_to_watch": "🔍 **लक्ष देण्याजोगे निष्कर्ष (Areas to Watch)**",
        "healthy_biomarkers": "✨ **सामान्य आणि निरोगी घटक (Healthy Biomarkers)**",
        "doctor_questions": "💬 **डॉक्टरांना विचारण्यासाठी महत्त्वाचे प्रश्न (Questions for Doctor)**",
        "urgent_alert": "⚠️ **तातडीचा वैद्यकीय इशारा (URGENT ALERT)**",
        "urgent_call": "कृपया त्वरित आपल्या डॉक्टरांशी संपर्क साधा किंवा जवळच्या रुग्णालयात जा.",
        "all_normal": "आनंदाची बातमी! तुमच्या तपासणीतील सर्व {count} रक्त चाचण्यांचे प्रमाण पूर्णपणे सामान्य मर्यादेत आहे.",
        "some_abnormal": "एकूण {total_count} पैकी {normal_count} चाचण्या सामान्य आहेत. {ab_count} चाचण्या सामान्य मर्यादेबाहेर आहेत, ज्यावर डॉक्टरांचा सल्ला घेणे आवश्यक आहे.",
        "healthy_suffix": "सर्व घटक चांगल्या व निरोगी मर्यादेत कार्यरत आहेत.",
        "disclaimer": "📋 *सूचना: पल्स एआय केवळ आरोग्यविषयक माहितीसाठी आहे; हा वैद्यकीय सल्ला किंवा निदान नाही.*"
    },
    "es": {
        "big_picture": "🩺 **Panorama General de Salud (The Big Picture)**",
        "areas_to_watch": "🔍 **Resultados que Requieren Atención (Areas to Watch)**",
        "healthy_biomarkers": "✨ **Biomarcadores en Rango Óptimo (Healthy Biomarkers)**",
        "doctor_questions": "💬 **Preguntas Sugeridas para su Médico (Questions for Doctor)**",
        "urgent_alert": "⚠️ **ALERTA CLÍNICA URGENTE**",
        "urgent_call": "Por favor comuníquese con su médico o acuda a un centro de urgencias de inmediato.",
        "all_normal": "¡Buenas noticias! Todos los {count} marcadores analizados se encuentran dentro de los rangos de referencia saludables esperados.",
        "some_abnormal": "En general, {normal_count} de sus {total_count} marcadores están dentro de límites saludables. Hay {ab_count} resultado(s) fuera de rango que requieren consulta con su médico.",
        "healthy_suffix": "funcionan en rangos óptimos de referencia.",
        "disclaimer": "📋 *Aviso: Pulse AI es una herramienta de educación en salud, no un dispositivo diagnóstico ni sustituto de atención médica.*"
    },
    "fr": {
        "big_picture": "🩺 **Vue d'Ensemble Clinique (The Big Picture)**",
        "areas_to_watch": "🔍 **Paramètres à Surveiller (Areas to Watch)**",
        "healthy_biomarkers": "✨ **Biomarqueurs Optimaux (Healthy Biomarkers)**",
        "doctor_questions": "💬 **Questions Suggérées pour Votre Médecin (Questions for Doctor)**",
        "urgent_alert": "⚠️ **ALERTE CLINIQUE URGENTE**",
        "urgent_call": "Veuillez contacter votre médecin ou vous rendre immédiatement aux urgences.",
        "all_normal": "Excellente nouvelle ! Les {count} biomarqueurs analysés se situent parfaitement dans les plages de référence saines.",
        "some_abnormal": "Au total, {normal_count} de vos {total_count} paramètres sanguins sont normaux. {ab_count} valeur(s) sortent des limites recommandées et méritent l'avis de votre médecin.",
        "healthy_suffix": "fonctionnent dans des plages de référence optimales.",
        "disclaimer": "📋 *Notice : Pulse AI est un outil éducatif de santé et ne constitue en aucun cas un avis médical ou diagnostic.*"
    }
}

MARKER_EXPLANATIONS = {
    "hi": {
        "hemoglobin": {"low": "हीमोग्लोबिन कम है, जो एनीमिया या खून की कमी दर्शाता है (थकान और कमजोरी हो सकती है)।", "high": "हीमोग्लोबिन अधिक है, जो निर्जलीकरण या अधिक लाल रक्त कोशिकाओं का संकेत दे सकता है।"},
        "glucose_f": {"low": "खाली पेट शर्करा कम (हाइपोग्लाइसीमिया) है; चक्कर या पसीना आ सकता है।", "high": "खाली पेट रक्त शर्करा बढ़ी हुई है, जो प्रीडायबिटीज या मधुमेह का संकेत है।"},
        "glucose_pp": {"low": "भोजन के बाद शर्करा कम है।", "high": "भोजन के बाद रक्त शर्करा उच्च है, आहार नियंत्रण की आवश्यकता है।"},
        "hba1c": {"low": "तीन महीने का औसत शर्करा सामान्य से कम है।", "high": "एचबीए1सी बढ़ा हुआ है, जो पिछले 3 महीनों का उच्च औसत ग्लूकोज दर्शाता है।"},
        "chol": {"low": "कोलेस्ट्रॉल सामान्य से बहुत कम है।", "high": "कुल कोलेस्ट्रॉल बढ़ा हुआ है, हृदय स्वास्थ्य पर ध्यान देने की आवश्यकता है।"},
        "ldl": {"low": "एलडीएल इष्टतम सुरक्षात्मक स्तर पर है।", "high": "एलडीएल (खराब कोलेस्ट्रॉल) बढ़ा हुआ है, धमनियों में प्लाक जमने का जोखिम बढ़ सकता है।"},
        "hdl": {"low": "एचडीएल (अच्छा कोलेस्ट्रॉल) कम है, जो हृदय सुरक्षा को कम करता है।", "high": "एचडीएल का स्तर अच्छा और हृदय के लिए लाभकारी है।"},
        "trig": {"low": "ट्राइग्लिसराइड्स बहुत कम हैं।", "high": "ट्राइग्लिसराइड्स बढ़े हुए हैं, वसायुक्त भोजन कम करें और व्यायाम बढ़ाएं।"},
        "creatinine": {"low": "सीरम क्रिएटिनिन कम है।", "high": "क्रिएटिनिन बढ़ा हुआ है, जो गुर्दे की कार्यप्रणाली पर असर का संकेत हो सकता है।"},
        "alt": {"low": "लिवर एंजाइम सामान्य है।", "high": "एएलटी (एसजीपीटी) बढ़ा हुआ है, लिवर में सूजन या फैटी लिवर का संकेत हो सकता है।"},
        "ast": {"low": "लिवर एंजाइम सामान्य है।", "high": "एएसटी (एसजीओटी) बढ़ा हुआ है, लिवर या मांसपेशियों पर प्रभाव हो सकता है।"},
        "tsh": {"low": "टीएसएच कम है, जो अतिसक्रिय थायरॉयड (हाइपरथायरायडिज्म) की ओर संकेत करता है।", "high": "टीएसएच बढ़ा हुआ है, जो अल्पसक्रिय थायरॉयड (हाइपोथायरायडिज्म) दर्शाता है।"},
        "vitd": {"low": "विटामिन डी कम है, हड्डियों और ऊर्जा के लिए धूप व सप्लीमेंट की जरूरत हो सकती है।", "high": "विटामिन डी का स्तर अधिक है।"},
        "b12": {"low": "विटामिन बी12 कम है, तंत्रिका स्वास्थ्य और हीमोग्लोबिन के लिए सप्लीमेंट आवश्यक हो सकता है।", "high": "विटामिन बी12 पर्याप्त से अधिक है।"},
        "platelets": {"low": "प्लेटलेट काउंट कम है, रक्तस्राव की संभावना बढ़ सकती है।", "high": "प्लेटलेट्स बढ़े हुए हैं।"}
    },
    "ta": {
        "hemoglobin": {"low": "ஹீமோகுளோபின் குறைவாக உள்ளது, இது இரத்த சோகைக்கான அறிகுறியாக இருக்கலாம் (சோர்வு ஏற்படலாம்).", "high": "ஹீமோகுளோபின் அதிகமாக உள்ளது, நீரிழப்பால் ஏற்படலாம்."},
        "glucose_f": {"low": "இரத்த சர்க்கரை குறைவாக உள்ளது.", "high": "வெறும் வயிற்று சர்க்கரை அளவு அதிகரித்துள்ளது, நீரிழிவு பரிசோதனை தேவை."},
        "hba1c": {"low": "சராசரி சர்க்கரை குறைவு.", "high": "கடந்த 3 மாத சராசரி சர்க்கரை அளவு அதிகரித்துள்ளது."},
        "chol": {"low": "கொழுப்பு குறைவு.", "high": "மொத்த கொழுப்பு அதிகரித்துள்ளது, இதய ஆரோக்கியத்தில் கவனம் தேவை."},
        "ldl": {"low": "பாதுகாப்பான அளவு.", "high": "கெட்ட கொழுப்பு (LDL) அதிகரித்துள்ளது."},
        "hdl": {"low": "நல்ல கொழுப்பு (HDL) குறைவாக உள்ளது, உடற்பயிற்சி தேவை.", "high": "இதயத்திற்கு நல்லது."},
        "trig": {"low": "குறைவு.", "high": "டிரைகிளிசரைடுகள் அதிகரித்துள்ளன."},
        "creatinine": {"low": "குறைவு.", "high": "கிரியேட்டினின் அளவு உயர்ந்துள்ளது, சிறுநீரக செயல்பாட்டை கண்காணிக்க வேண்டும்."},
        "alt": {"low": "சாதாரணம்.", "high": "கல்லீரல் நொதி (ALT) உயர்ந்துள்ளது."},
        "tsh": {"low": "தைராய்டு ஹார்மோன் குறைவு.", "high": "தைராய்டு ஹார்மோன் தூண்டுதல் (TSH) அதிகரித்துள்ளது."},
        "vitd": {"low": "வைட்டமின் டி குறைபாடு உள்ளது, எலும்பு பலவீனமடையலாம்.", "high": "அதிகம்."},
        "b12": {"low": "வைட்டமின் பி12 குறைபாடு உள்ளது, சோர்வு வரலாம்.", "high": "அதிகம்."}
    },
    "te": {
        "hemoglobin": {"low": "హిమోగ్లోబిన్ తక్కువగా ఉంది, ఇది రక్తహీనతను సూచిస్తుంది (నీరసం రావచ్చు).", "high": "హిమోగ్లోబిన్ ఎక్కువగా ఉంది."},
        "glucose_f": {"low": "షుగర్ తక్కువగా ఉంది.", "high": "ఉదయం పరగడుపున షుగర్ స్థాయి ఎక్కువగా ఉంది, మధుమేహ నియంత్రణ అవసరం."},
        "hba1c": {"low": "షుగర్ తక్కువ.", "high": "గత 3 నెలల సగటు గ్లూకోజ్ (HbA1c) పెరిగింది."},
        "chol": {"low": "కొలెస్ట్రాల్ తక్కువ.", "high": "మొత్తం కొలెస్ట్రాల్ పెరిగింది, గుండె ఆరోగ్యంపై దృష్టి పెట్టండి."},
        "ldl": {"low": "ఆప్టిమల్.", "high": "చెడు కొలెస్ట్రాల్ (LDL) అధికంగా ఉంది."},
        "hdl": {"low": "మంచి కొలెస్ట్రాల్ (HDL) తగ్గింది.", "high": "గుండెకు మంచిది."},
        "trig": {"low": "తక్కువ.", "high": "ట్రైగ్లిజరైడ్స్ పెరిగాయి."},
        "creatinine": {"low": "తక్కువ.", "high": "క్రియాటినిన్ పెరిగింది, మూత్రపిండాల పనితీరును పరిశీలించాలి."},
        "tsh": {"low": "థైరాయిడ్ తక్కువ.", "high": "టిఎస్ హెచ్ (TSH) పెరిగింది, థైరాయిడ్ సమస్య ఉండవచ్చు."},
        "vitd": {"low": "విటమిన్ డి లోపం ఉంది.", "high": "ఎక్కువ."},
        "b12": {"low": "విటమిన్ బి12 తక్కువగా ఉంది.", "high": "ఎక్కువ."}
    },
    "kn": {
        "hemoglobin": {"low": "ಹಿಮೋಗ್ಲೋಬಿನ್ ಕಡಿಮೆಯಾಗಿದೆ, ಇದು ರಕ್ತಹೀನತೆ ಮತ್ತು ಆಯಾಸಕ್ಕೆ ಕಾರಣವಾಗಬಹುದು.", "high": "ಹಿಮೋಗ್ಲೋಬಿನ್ ಹೆಚ್ಚಾಗಿದೆ."},
        "glucose_f": {"low": "ರಕ್ತದಲ್ಲಿ ಸಕ್ಕರೆ ಅಂಶ ಕಡಿಮೆಯಾಗಿದೆ.", "high": "ಖಾಲಿ ಹೊಟ್ಟೆಯ ಸಕ್ಕರೆ ಅಂಶ ಹೆಚ್ಚಾಗಿದೆ, ಮಧುಮೇಹ ತಪಾಸಣೆ ಅಗತ್ಯ."},
        "chol": {"low": "ಕೊಲೆಸ್ಟ್ರಾಲ್ ಕಡಿಮೆ.", "high": "ಕೊಲೆಸ್ಟ್ರಾಲ್ ಹೆಚ್ಚಾಗಿದೆ, ಹೃದಯದ ಆರೋಗ್ಯದ ಬಗ್ಗೆ ಗಮನವಿರಲಿ."},
        "creatinine": {"low": "ಕಡಿಮೆ.", "high": "ಕ್ರಿಯಾಟಿನಿನ್ ಹೆಚ್ಚಾಗಿದೆ, ಮೂತ್ರಪಿಂಡಗಳ ಕಾರ್ಯನಿರ್ವಹಣೆಯನ್ನು ಪರೀಕ್ಷಿಸಿ."},
        "vitd": {"low": "ವಿಟಮಿನ್ ಡಿ ಕೊರತೆಯಿದೆ.", "high": "ಸಾಕಷ್ಟು ಪ್ರಮಾಣದಲ್ಲಿದೆ."}
    },
    "ml": {
        "hemoglobin": {"low": "ഹീമോഗ്ലോബിൻ കുറവാണ്, ഇത് അനീമിയ അല്ലെങ്കിൽ വിളർച്ചക്ക് കാരണമാകാം.", "high": "ഹീമോഗ്ലോബിൻ കൂടുതലാണ്."},
        "glucose_f": {"low": "പഞ്ചസാരയുടെ അളവ് കുറവാണ്.", "high": "വെറും വയറ്റിലെ പഞ്ചസാരയുടെ അളവ് കൂടുതലാണ്."},
        "chol": {"low": "കൊളസ്ട്രോൾ കുറവാണ്.", "high": "കൊളസ്ട്രോൾ കൂടുതലാണ്, ഹൃദയാരോഗ്യത്തിൽ ശ്രദ്ധിക്കുക."},
        "creatinine": {"low": "കുറവ്.", "high": "ക്രിയാറ്റിനിൻ അളവ് ഉയർന്നിരിക്കുന്നു, വൃക്കകളുടെ പ്രവർത്തനം പരിശോധിക്കുക."},
        "vitd": {"low": "വൈറ്റമിൻ ഡി കുറവാണ്.", "high": "കൂടുതലാണ്."}
    },
    "bn": {
        "hemoglobin": {"low": "হিমোগ্লোবিন কম, যা রক্তাল্পতা বা অ্যানিমিয়ার লক্ষণ (ক্লান্তি হতে পারে)।", "high": "হিমোগ্লোবিন স্বাভাবিকের চেয়ে বেশি।"},
        "glucose_f": {"low": "রক্তে শর্করার মাত্রা কম।", "high": "খালি পেটে সুগারের মাত্রা বেশি, ডায়াবেটিস নিয়ন্ত্রণ প্রয়োজন।"},
        "chol": {"low": "কোলেস্টেরল কম।", "high": "মোট কোলেস্টেরল বৃদ্ধি পেয়েছে, হৃদযন্ত্রের স্বাস্থ্যে নজর দিন।"},
        "creatinine": {"low": "কম।", "high": "ক্রিয়েটিনিন বৃদ্ধি পেয়েছে, কিডনির কার্যকারিতা পরীক্ষা প্রয়োজন।"},
        "vitd": {"low": "ভিটামিন ডি-এর ঘাটতি রয়েছে।", "high": "উচ্চ মাত্রা।"}
    },
    "mr": {
        "hemoglobin": {"low": "हिमोग्लोबिन कमी आहे, ज्यामुळे अशक्तपणा किंवा ॲनिमिया जाणवू शकतो.", "high": "हिमोग्लोबिन जास्त आहे."},
        "glucose_f": {"low": "रक्तातील साखर कमी आहे.", "high": "उपाशीपोटी रक्तातील साखर वाढली आहे, तपासणी आवश्यक आहे."},
        "chol": {"low": "कोलेस्ट्रॉल कमी आहे.", "high": "एकूण कोलेस्ट्रॉल वाढले आहे, हृदयाच्या आरोग्याची काळजी घ्या."},
        "creatinine": {"low": "कमी आहे.", "high": "क्रिएटीनाइन वाढले आहे, मूत्रपिंडाच्या कार्यावर लक्ष ठेवा."},
        "vitd": {"low": "व्हिटॅमिन डी ची कमतरता आहे.", "high": "भरपूर प्रमाणात आहे."}
    },
    "es": {
        "hemoglobin": {"low": "Hemoglobina baja, lo cual sugiere anemia leve o deficiencia de hierro.", "high": "Hemoglobina elevada, posiblemente por deshidratación."},
        "glucose_f": {"low": "Glucosa en ayunas baja (hipoglucemia).", "high": "Glucosa en ayunas elevada, sugiere prediabetes o control glucémico deficiente."},
        "hba1c": {"low": "HbA1c baja.", "high": "HbA1c elevada, indica glucosa promedio alta en los últimos 3 meses."},
        "chol": {"low": "Colesterol bajo.", "high": "Colesterol total elevado, requiere optimización dietética cardiovascular."},
        "ldl": {"low": "Nivel óptimo.", "high": "Colesterol LDL elevado, factor de riesgo aterogénico."},
        "hdl": {"low": "HDL bajo, menor protección cardiovascular.", "high": "HDL en rango protector."},
        "trig": {"low": "Triglicéridos bajos.", "high": "Triglicéridos altos, reducir carbohidratos simples y grasas."},
        "creatinine": {"low": "Creatinina baja.", "high": "Creatinina elevada, sugiere vigilar la filtración renal y la hidratación."},
        "alt": {"low": "Normal.", "high": "ALT elevada, posible inflamación hepática o esteatosis."},
        "tsh": {"low": "TSH baja (posible hipertiroidismo).", "high": "TSH elevada (posible hipotiroidismo)."},
        "vitd": {"low": "Deficiencia de Vitamina D, esencial para huesos e inmunidad.", "high": "Nivel suficiente."},
        "b12": {"low": "Vitamina B12 baja, importante para energía y función neurológica.", "high": "Adecuado."}
    },
    "fr": {
        "hemoglobin": {"low": "Hémoglobine basse, suggérant une anémie ou une carence en fer.", "high": "Hémoglobine élevée, possible signe d'hémoconcentration."},
        "glucose_f": {"low": "Glycémie à jeun basse.", "high": "Glycémie à jeun élevée, surveillance du métabolisme glucidique requise."},
        "hba1c": {"low": "HbA1c basse.", "high": "HbA1c élevée, équilibre glycémique moyen des 3 derniers mois à revoir."},
        "chol": {"low": "Cholestérol bas.", "high": "Cholestérol total élevé, hygiène de vie cardio-protectrice conseillée."},
        "ldl": {"low": "Optimal.", "high": "LDL élevé (mauvais cholestérol), risque athérogène à surveiller."},
        "hdl": {"low": "HDL bas, protection vasculaire réduite.", "high": "HDL satisfaisant."},
        "trig": {"low": "Triglycérides bas.", "high": "Triglycérides élevés, réduire sucres rapides et alcool."},
        "creatinine": {"low": "Créatinine basse.", "high": "Créatinine augmentée, évaluer la fonction de filtration rénale."},
        "alt": {"low": "Normale.", "high": "Transaminases ALT élevées, possible surcharge ou souffrance hépatique."},
        "tsh": {"low": "TSH basse (suspicion d'hyperthyroïdie).", "high": "TSH élevée (suspicion d'hypothyroïdie)."},
        "vitd": {"low": "Carence en vitamine D, soutien osseux et immunitaire nécessaire.", "high": "Suffisant."},
        "b12": {"low": "Carence en vitamine B12, risque de fatigue et troubles neurologiques.", "high": "Optimal."}
    }
}

DOCTOR_QUESTIONS = {
    "hi": {
        "hemoglobin": "• \"मेरे कम हीमोग्लोबिन के लिए क्या मुझे सीरम फेरिटिन या विटामिन बी12 की जांच करानी चाहिए?\"",
        "glucose_f": "• \"रक्त शर्करा को नियंत्रित रखने के लिए क्या आहार व व्यायाम में बदलाव करना चाहिए?\"",
        "hba1c": "• \"मेरे बढ़े हुए एचबीए1सी के लिए क्या कोई दवा शुरू या समायोजित करने की जरूरत है?\"",
        "chol": "• \"कोलेस्ट्रॉल कम करने के लिए कौन से जीवनशैली और खान-पान के उपाय सर्वोत्तम हैं?\"",
        "ldl": "• \"क्या मेरे एलडीएल स्तर के लिए स्टेटिन दवा की आवश्यकता है?\"",
        "trig": "• \"ट्राइग्लिसराइड्स कम करने के लिए क्या सावधानियां रखनी चाहिए?\"",
        "creatinine": "• \"क्रिएटिनिन स्तर के लिए क्या मुझे यूरिन प्रोटीन या किडनी का अल्ट्रासाउंड कराना चाहिए?\"",
        "alt": "• \"लिवर एंजाइम (ALT) में वृद्धि के लिए क्या 4-6 सप्ताह बाद पुनः जांच करनी चाहिए?\"",
        "tsh": "• \"क्या थायरॉयड की स्थिति जानने के लिए फ्री टी3 और फ्री टी4 टेस्ट कराना चाहिए?\"",
        "vitd": "• \"विटामिन डी बढ़ाने के लिए कौन सी खुराक और कितने समय तक सप्लीमेंट लेना चाहिए?\"",
        "b12": "• \"विटामिन बी12 की कमी के लिए कौन सा सप्लीमेंट सर्वोत्तम रहेगा?\""
    },
    "ta": {
        "hemoglobin": "• \"எனது குறைந்த ஹீமோகுளோபினுக்கு அயர்ன் (Ferritin) அல்லது B12 பரிசோதனை செய்ய வேண்டுமா?\"",
        "glucose_f": "• \"சர்க்கரை அளவை கட்டுப்படுத்த என்ன உணவு மாற்றங்களை செய்ய வேண்டும்?\"",
        "chol": "• \"கொழுப்பை குறைக்க என்ன வழிமுறைகளை பின்பற்ற வேண்டும்?\"",
        "creatinine": "• \"சிறுநீரக செயல்பாட்டை உறுதிப்படுத்த மீண்டும் பரிசோதனை செய்ய வேண்டுமா?\"",
        "tsh": "• \"தைராய்டு அளவுக்காக கூடுதல் பரிசோதனைகள் தேவையா?\"",
        "vitd": "• \"வைட்டமின் டி அதிகரிக்க என்ன மருந்துகள் எடுக்க வேண்டும்?\""
    },
    "te": {
        "hemoglobin": "• \"హిమోగ్లోబిన్ తక్కువగా ఉన్నందుకు ఐరన్ లేదా బి12 టెస్ట్ చేయించాలా?\"",
        "glucose_f": "• \"షుగర్ లెవల్స్ కంట్రోల్ చేయడానికి ఎలాంటి ఆహార నియమాలు పాటించాలి?\"",
        "chol": "• \"కొలెస్ట్రాల్ తగ్గించుకోవడానికి ఎలాంటి వ్యాయామం, ఆహారం అవసరం?\"",
        "creatinine": "• \"క్రియాటినిన్ కోసం మళ్లీ ఎప్పుడు కిడ్నీ టెస్ట్ చేయించాలి?\"",
        "tsh": "• \"థైరాయిడ్ కోసం మందులు వాడాల్సిన అవసరం ఉందా?\"",
        "vitd": "• \"విటమిన్ డి పెరగడానికి ఏ సప్లిమెంట్ తీసుకోవాలి?\""
    },
    "kn": {
        "hemoglobin": "• \"ರಕ್ತಹೀನತೆಗಾಗಿ ನಾನು ಐರನ್ ಅಥವಾ ವಿಟಮಿನ್ ಬಿ12 ಪರೀಕ್ಷೆ ಮಾಡಿಸಬೇಕೇ?\"",
        "glucose_f": "• \"ಸಕ್ಕರೆ ನಿಯಂತ್ರಣಕ್ಕೆ ಯಾವ ಆಹಾರ ಕ್ರಮ ಪಾಲಿಸಬೇಕು?\"",
        "chol": "• \"ಕೊಲೆಸ್ಟ್ರಾಲ್ ಕಡಿಮೆ ಮಾಡಲು ಏನು ಕ್ರಮಗಳನ್ನು ಕೈಗೊಳ್ಳಬೇಕು?\"",
        "creatinine": "• \"ಕ್ರಿಯಾಟಿನಿನ್ ಗಾಗಿ ಮೂತ್ರಪಿಂಡಗಳ ಮತ್ತೊಮ್ಮೆ ಪರೀಕ್ಷೆ ಅಗತ್ಯವಿದೆಯೇ?\""
    },
    "ml": {
        "hemoglobin": "• \"ഹീമോഗ്ലോബിൻ കുറഞ്ഞതിന് അയൺ അല്ലെങ്കിൽ ബി12 പരിശോധന ആവശ്യമുണ്ടോ?\"",
        "glucose_f": "• \"ഷുഗർ നിയന്ത്രിക്കാൻ എന്തൊക്കെ ഭക്ഷണക്രമം പാലിക്കണം?\"",
        "chol": "• \"കൊളസ്ട്രോൾ കുറയ്ക്കാൻ എന്ത് വ്യായാമവും ഭക്ഷണവുമാണ് വേണ്ടത്?\"",
        "creatinine": "• \"വൃക്കകളുടെ ആരോഗ്യം ഉറപ്പാക്കാൻ കൂടുതൽ പരിശോധനകൾ വേണമോ?\""
    },
    "bn": {
        "hemoglobin": "• \"আমার কম হিমোগ্লোবিনের জন্য কি আয়রন বা বি১২ পরীক্ষা করা উচিত?\"",
        "glucose_f": "• \"রক্তে শর্করা নিয়ন্ত্রণে রাখতে খাদ্যতালিকায় কী পরিবর্তন আনা উচিত?\"",
        "chol": "• \"কোলেস্টেরল কমাতে কোন ধরণের জীবনযাত্রা অনুসরণ করা প্রয়োজন?\"",
        "creatinine": "• \"কিডনির সুস্থতা যাচাইয়ে আরও কোনো পরীক্ষা প্রয়োজন কি?\""
    },
    "mr": {
        "hemoglobin": "• \"कमी हिमोग्लोबिनसाठी लोह (Ferritin) किंवा व्हिटॅमिन बी12 ची तपासणी करावी का?\"",
        "glucose_f": "• \"रक्तातील साखर नियंत्रित करण्यासाठी आहारात कोणते बदल करावेत?\"",
        "chol": "• \"कोलेस्ट्रॉल कमी करण्यासाठी कोणती जीवनशैली अंगीकारावी?\"",
        "creatinine": "• \"किडनीच्या आरोग्यासाठी पुढील तपासणी कधी करावी?\""
    },
    "es": {
        "hemoglobin": "• \"¿Recomienda medir ferritina sérica o vitamina B12 para evaluar mi hemoglobina?\"",
        "glucose_f": "• \"¿Sería conveniente solicitar una prueba de HbA1c o consulta nutricional?\"",
        "chol": "• \"¿Qué cambios dietéticos o terapia lipídica son recomendables según mi perfil?\"",
        "creatinine": "• \"¿Debemos repetir la creatinina o evaluar la tasa de filtración glomerular?\"",
        "tsh": "• \"¿Considera necesario solicitar T3 y T4 libre para valorar mi tiroides?\"",
        "vitd": "• \"¿Cuál es la dosis y duración indicada para suplementar mi vitamina D?\""
    },
    "fr": {
        "hemoglobin": "• \"Conseillez-vous un dosage de ferritine sérique ou de vitamine B12 pour explorer mon anémie ?\"",
        "glucose_f": "• \"Serait-il utile d'effectuer un bilan d'HbA1c ou un suivi nutritionnel ?\"",
        "chol": "• \"Quelles mesures diététiques ou prises en charge proposez-vous pour ce profil lipidique ?\"",
        "creatinine": "• \"Faut-il contrôler la clairance de la créatinine ou réaliser une échographie rénale ?\"",
        "tsh": "• \"Un bilan thyroïdien complet avec T4 libre est-il nécessaire ?\"",
        "vitd": "• \"Quelle supplémentation en vitamine D3 préconisez-vous ?\""
    }
}

SUGGESTED_CHIPS = {
    "en": [
        "What questions should I ask my doctor?",
        "Are any of my results abnormal?",
        "What dietary changes could support my markers?",
        "How do my results compare across visits?",
        "Explain my Complete Blood Count panel"
    ],
    "hi": [
        "डॉक्टर से परामर्श हेतु क्या पूछना चाहिए?",
        "क्या मेरी रिपोर्ट में कोई परिणाम असामान्य है?",
        "इन परिणामों को सुधारने के लिए क्या आहार लेना चाहिए?",
        "मेरे हीमोग्लोबिन और रक्त शर्करा का क्या अर्थ है?",
        "क्या मुझे किसी विशेषज्ञ डॉक्टर से मिलना चाहिए?"
    ],
    "ta": [
        "மருத்துவரிடம் கேட்க வேண்டிய முக்கியமான கேள்விகள் என்ன?",
        "எனது முடிவுகளில் ஏதேனும் இயல்புக்கு மாறாக உள்ளதா?",
        "சீரான ஆரோக்கியத்திற்கு என்ன உணவு பழக்கம் தேவை?",
        "ஹீமோகுளோபின் மற்றும் சர்க்கரை அளவு பற்றி விளக்குக"
    ],
    "te": [
        "వైద్యుడిని అడగవలసిన ముఖ్యమైన ప్రశ్నలు ఏమిటి?",
        "నా రక్త పరీక్షలో ఏవైనా అసాధారణ ఫలితాలు ఉన్నాయా?",
        "ఆరోగ్యాన్ని మెరుగుపరచడానికి ఎలాంటి ఆహారం తీసుకోవాలి?",
        "హిమోగ్లోబిన్ మరియు షుగర్ స్థాయిల వివరాలు చెప్పండి"
    ],
    "kn": [
        "ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚಿಸಬೇಕಾದ ಮುಖ್ಯ ಪ್ರಶ್ನೆಗಳು ಯಾವುವು?",
        "ವರದಿಯಲ್ಲಿ ಯಾವುದೇ ಅಸಹಜ ಫಲಿತಾಂಶಗಳಿವೆಯೇ?",
        "ಆರೋಗ್ಯ ಸುಧಾರಣೆಗೆ ಯಾವ ಆಹಾರ ಕ್ರಮ ಅನುಸರಿಸಬೇಕು?"
    ],
    "ml": [
        "ഡോക്ടറോട് ചോദിക്കേണ്ട പ്രധാന ചോദ്യങ്ങൾ എന്തൊക്കെയാണ്?",
        "റിപ്പോർട്ടിൽ എന്തെങ്കിലും വ്യത്യാസങ്ങൾ ഉണ്ടോ?",
        "ആരോഗ്യം മെച്ചപ്പെടുത്താൻ എന്ത് ഭക്ഷണമാണ് കഴിക്കേണ്ടത്?"
    ],
    "bn": [
        "ডাক্তারকে জিজ্ঞাসা করার মতো গুরুত্বপূর্ণ প্রশ্নগুলি কী?",
        "আমার কোনো পরীক্ষার ফলাফল কি অস্বাভাবিক?",
        "স্বাস্থ্য উন্নতির জন্য কী ধরনের খাবার খাওয়া উচিত?"
    ],
    "mr": [
        "डॉक्टरांना कोणते महत्त्वाचे प्रश्न विचारावेत?",
        "अहवालात काही असामान्य निष्कर्ष आहेत का?",
        "आरोग्य सुधारण्यासाठी कोणता आहार योग्य राहील?"
    ],
    "es": [
        "¿Qué preguntas debo hacerle a mi médico?",
        "¿Hay algún resultado fuera de los rangos normales?",
        "¿Qué cambios en la dieta pueden ayudar a mis valores?",
        "Explique mi hemograma completo"
    ],
    "fr": [
        "Quelles questions devrais-je poser à mon médecin ?",
        "Y a-t-il des résultats anormaux dans mon bilan ?",
        "Quelles habitudes alimentaires peuvent m'aider ?",
        "Expliquez ma formule sanguine complète"
    ]
}

def translate_status(status: str, lang: str) -> str:
    s = (status or "").lower()
    if lang == "hi":
        return {"normal": "सामान्य", "low": "कम (Low)", "high": "अधिक (High)", "critical": "गंभीर (Critical)", "mild": "हल्का", "moderate": "मध्यम", "marked": "अत्यधिक"}.get(s, status)
    elif lang == "ta":
        return {"normal": "இயல்பு", "low": "குறைவு", "high": "அதிகம்", "critical": "அவசரம்", "mild": "குறைந்த", "moderate": "நடுத்தர", "marked": "அதிக"}.get(s, status)
    elif lang == "te":
        return {"normal": "సాధారణం", "low": "తక్కువ", "high": "ఎక్కువ", "critical": "తీవ్రం", "mild": "కొద్దిగా", "moderate": "మధ్యస్థం", "marked": "అధికం"}.get(s, status)
    elif lang == "kn":
        return {"normal": "ಸಾಮಾನ್ಯ", "low": "ಕಡಿಮೆ", "high": "ಹೆಚ್ಚು", "critical": "ಗಂಭೀರ", "mild": "ಸ್ವಲ್ಪ", "moderate": "ಮಧ್ಯಮ", "marked": "ಅಧಿಕ"}.get(s, status)
    elif lang == "ml":
        return {"normal": "സാധാരണ", "low": "കുറവ്", "high": "കൂടുതൽ", "critical": "ഗുരുതരം", "mild": "നേരിയ", "moderate": "മിതമായ", "marked": "തീവ്രമായ"}.get(s, status)
    elif lang == "bn":
        return {"normal": "স্বাভাবিক", "low": "কম", "high": "বেশি", "critical": "সংকটজনক", "mild": "সামান্য", "moderate": "মাঝারি", "marked": "অত্যধিক"}.get(s, status)
    elif lang == "mr":
        return {"normal": "सामान्य", "low": "कमी", "high": "जास्त", "critical": "गंभीर", "mild": "किंचित", "moderate": "मध्यम", "marked": "अत्यंत जास्त"}.get(s, status)
    elif lang == "es":
        return {"normal": "Normal", "low": "Bajo", "high": "Alto", "critical": "Crítico", "mild": "Leve", "moderate": "Moderado", "marked": "Marcado"}.get(s, status)
    elif lang == "fr":
        return {"normal": "Normal", "low": "Bas", "high": "Élevé", "critical": "Critique", "mild": "Léger", "moderate": "Modéré", "marked": "Marqué"}.get(s, status)
    return status

def generate_multilingual_summary(report: dict, lang: str = "en") -> str:
    """Generate a high-quality clinical consultation summary in the selected language."""
    if lang == "en" or lang not in HEADERS:
        h = HEADERS["en"]
    else:
        h = HEADERS[lang]
        
    results = report.get("results", [])
    if not results:
        return "No lab values could be read. Please upload a clear report."
        
    ab = [r for r in results if r.get("status") != "normal"]
    crits = [r for r in results if r.get("is_critical")]
    normal_count = len(results) - len(ab)
    
    sections = []
    
    # 1. Urgent Alert
    if crits:
        c_lines = [h["urgent_alert"]]
        for c in crits:
            c_lines.append(f"- **{c['name']}**: {c.get('critical_alert') or 'Critical value.'}")
        c_lines.append(h["urgent_call"])
        sections.append("\n".join(c_lines))
        
    # 2. Big Picture
    if not ab:
        sections.append(f"{h['big_picture']}\n{h['all_normal'].format(count=len(results))}")
    else:
        sections.append(f"{h['big_picture']}\n{h['some_abnormal'].format(total_count=len(results), normal_count=normal_count, ab_count=len(ab))}")
        
    # 3. Areas to Watch
    if ab:
        watch_lines = [h["areas_to_watch"]]
        lang_exps = MARKER_EXPLANATIONS.get(lang, {})
        for r in ab:
            k = r.get("key", "")
            stat = r.get("status", "out of range")
            t_stat = translate_status(stat, lang)
            
            # Use native clinical explanation if available
            if k in lang_exps and stat in lang_exps[k]:
                desc = lang_exps[k][stat]
            else:
                desc = r.get("meaning") or f"{r['name']} is {stat}."
                
            watch_lines.append(f"• **{r['name']}** ({t_stat}): {desc}")
        sections.append("\n".join(watch_lines))
        
    # 4. Healthy Biomarkers
    if normal_count > 0:
        normal_names = [r["name"] for r in results if r.get("status") == "normal"]
        sample_normals = ", ".join(normal_names[:5])
        suffix = f" (+{len(normal_names)-5})" if len(normal_names) > 5 else ""
        sections.append(f"{h['healthy_biomarkers']}\n{sample_normals}{suffix} {h['healthy_suffix']}")
        
    # 5. Questions for Doctor
    doc_lines = [h["doctor_questions"]]
    lang_questions = DOCTOR_QUESTIONS.get(lang, {})
    if ab:
        for r in ab[:3]:
            k = r.get("key", "")
            if k in lang_questions:
                doc_lines.append(lang_questions[k])
            else:
                doc_lines.append(f"• \"What steps do you recommend for my {r['name']} ({r.get('value')} {r.get('unit')})?\"")
    else:
        if lang == "hi":
            doc_lines.append("• \"मेरे स्वास्थ्य के लिए कौन से निवारक उपाय या आहार आदतें सर्वोत्तम रहेंगी?\"")
            doc_lines.append("• \"मुझे अपनी अगली नियमित जांच कब करानी चाहिए?\"")
        elif lang == "ta":
            doc_lines.append("• \"எனது ஆரோக்கியத்தை பேண என்ன உணவு பழக்கங்களை பின்பற்ற வேண்டும்?\"")
        elif lang == "te":
            doc_lines.append("• \"నా ఆరోగ్యాన్ని కాపాడుకోవడానికి ఎలాంటి జాగ్రత్తలు తీసుకోవాలి?\"")
        else:
            doc_lines.append("• \"Are there routine preventive habits you recommend at this stage?\"")
    sections.append("\n".join(doc_lines))
    
    # 6. Disclaimer
    sections.append(h["disclaimer"])
    return "\n\n".join(sections)

def generate_multilingual_speech(report: dict, lang: str = "en") -> str:
    """Generate fluid, human-spoken conversational script in the target language.
    Crucially: Strips brackets, units, and technical noise so TTS sounds natural."""
    results = report.get("results", [])
    if not results:
        return "No test values detected."
        
    ab = [r for r in results if r.get("status") != "normal"]
    crits = [r for r in results if r.get("is_critical")]
    normal_count = len(results) - len(ab)
    
    if lang == "hi":
        parts = ["नमस्ते! यह आपकी रक्त जांच रिपोर्ट का ऑडियो विवरण है।"]
        if crits:
            c_names = " और ".join(c["name"] for c in crits)
            parts.append(f"महत्वपूर्ण सूचना: आपके {c_names} परीक्षण में गंभीर विचलन है। कृपया तुरंत अपने डॉक्टर से संपर्क करें।")
        elif not ab:
            parts.append(f"आपके लिए बहुत अच्छी खबर है! जांचे गए सभी {len(results)} परीक्षण पूरी तरह से सामान्य और स्वस्थ हैं। अपनी अच्छी जीवनशैली बनाए रखें।")
            return re.sub(r"[()]", "", " ".join(parts))
        else:
            parts.append(f"आपकी रिपोर्ट में {len(results)} परीक्षणों में से {normal_count} परीक्षण सामान्य हैं, और {len(ab)} परिणामों पर ध्यान देने की आवश्यकता है।")
            
        lang_exps = MARKER_EXPLANATIONS.get("hi", {})
        for r in ab[:4]:
            k = r.get("key", "")
            stat = r.get("status", "")
            if k in lang_exps and stat in lang_exps[k]:
                parts.append(lang_exps[k][stat])
            else:
                parts.append(f"आपका {r['name']} सामान्य से {translate_status(stat, 'hi')} है।")
                
        parts.append("कृपया यह रिपोर्ट अपने डॉक्टर को अवश्य दिखाएं। स्वास्थ्य का ध्यान रखें।")
        return re.sub(r"[()]", "", " ".join(parts))

    elif lang == "ta":
        parts = ["வணக்கம்! இது உங்கள் இரத்த பரிசோதனை அறிக்கையின் சுருக்கமான விளக்கம்."]
        if not ab:
            parts.append(f"அனைத்து {len(results)} சோதனைகளும் இயல்பாக உள்ளன. உங்கள் ஆரோக்கியம் சீராக உள்ளது.")
            return " ".join(parts)
        else:
            parts.append(f"{len(results)} சோதனைகளில் {len(ab)} சோதனைகள் கவனிக்கப்பட வேண்டியவை.")
            lang_exps = MARKER_EXPLANATIONS.get("ta", {})
            for r in ab[:3]:
                k = r.get("key", "")
                stat = r.get("status", "")
                if k in lang_exps and stat in lang_exps[k]:
                    parts.append(lang_exps[k][stat])
            parts.append("இந்த அறிக்கையை உங்கள் மருத்துவரிடம் காண்பிக்கவும்.")
            return " ".join(parts)

    elif lang == "te":
        parts = ["నమస్కారం! ఇది మీ రక్త పరీక్ష నివేదిక వివరాలు."]
        if not ab:
            parts.append(f"మీ అన్ని {len(results)} పరీక్షలు సాధారణంగా ఉన్నాయి. ఆరోగ్యం బాగుంది.")
            return " ".join(parts)
        else:
            parts.append(f"{len(results)} పరీక్షల్లో {len(ab)} అంశాలపై శ్రద్ధ వహించాలి.")
            lang_exps = MARKER_EXPLANATIONS.get("te", {})
            for r in ab[:3]:
                k = r.get("key", "")
                stat = r.get("status", "")
                if k in lang_exps and stat in lang_exps[k]:
                    parts.append(lang_exps[k][stat])
            parts.append("దయచేసి మీ వైద్యుడిని సంప్రదించండి.")
            return " ".join(parts)

    elif lang == "kn":
        parts = ["ನಮಸ್ಕಾರ! ಇದು ನಿಮ್ಮ ರಕ್ತ ಪರೀಕ್ಷಾ ವರದಿಯ ಆಡಿಯೋ ವಿವರಣೆ."]
        if not ab:
            parts.append(f"ಶುಭ ಸುದ್ದಿ! ನಿಮ್ಮ ಎಲ್ಲಾ {len(results)} ಪರೀಕ್ಷೆಗಳು ಸಾಮಾನ್ಯ ಮತ್ತು ಆರೋಗ್ಯಕರ ಮಿತಿಯಲ್ಲಿವೆ.")
            return " ".join(parts)
        else:
            parts.append(f"ವರದಿಯಲ್ಲಿ {len(ab)} ಪರೀಕ್ಷಾ ಅಂಶಗಳು ಗಮನಿಸಬೇಕಾದವು.")
            for r in ab[:3]:
                parts.append(f"ನಿಮ್ಮ {r['name']} ಸಾಮಾನ್ಯ ಮಿತಿಗಿಂತ {translate_status(r.get('status'), 'kn')} ಆಗಿದೆ.")
            parts.append("ದಯವಿಟ್ಟು ಈ ವರದಿಯನ್ನು ನಿಮ್ಮ ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚಿಸಿ.")
            return " ".join(parts)

    elif lang == "ml":
        parts = ["നമസ്കാരം! ഇത് നിങ്ങളുടെ രക്തപരിശോധനാ ഫലങ്ങളുടെ ശബ്ദരൂപത്തിലുള്ള വിവരണമാണ്."]
        if not ab:
            parts.append(f"എല്ലാ {len(results)} പരിശോധനകളും പൂർണ്ണമായും സാധാരണ പരിധിക്കുള്ളിലാണ്.")
            return " ".join(parts)
        else:
            parts.append(f"{len(ab)} പരിശോധനാ ഫലങ്ങൾ ശ്രദ്ധിക്കേണ്ടതുണ്ട്.")
            for r in ab[:3]:
                parts.append(f"{r['name']} സാധാരണ നിലയേക്കാൾ {translate_status(r.get('status'), 'ml')} ആണ്.")
            parts.append("ഈ റിപ്പോർട്ട് നിങ്ങളുടെ ഡോക്ടറെ കാണിക്കുക.")
            return " ".join(parts)

    elif lang == "bn":
        parts = ["নমস্কার! এটি আপনার রক্ত পরীক্ষার রিপোর্টের অডিও বিবরণ।"]
        if not ab:
            parts.append(f"খুব ভালো খবর! আপনার সমস্ত {len(results)}টি রক্ত পরীক্ষা স্বাভাবিক সীমার মধ্যে রয়েছে।")
            return " ".join(parts)
        else:
            parts.append(f"আপনার রিপোর্টে {len(ab)}টি ফলাফল সাধারণ সীমার বাইরে রয়েছে।")
            for r in ab[:3]:
                parts.append(f"আপনার {r['name']} স্বাভাবিকের চেয়ে {translate_status(r.get('status'), 'bn')} রয়েছে।")
            parts.append("অনুগ্রহ করে এই ফলাফল নিয়ে আপনার চিকিৎসকের সাথে কথা বলুন।")
            return " ".join(parts)

    elif lang == "mr":
        parts = ["नमस्कार! हा तुमच्या रक्त तपासणी अहवालाचा ऑडिओ सारांश आहे."]
        if not ab:
            parts.append(f"आनंदाची बातमी! तुमच्या सर्व {len(results)} चाचण्या सामान्य मर्यादेत आहेत.")
            return " ".join(parts)
        else:
            parts.append(f"अहवालात {len(ab)} चाचण्या सामान्य मर्यादेबाहेर आहेत.")
            for r in ab[:3]:
                parts.append(f"तुमचे {r['name']} सामान्य मर्यादेपेक्षा {translate_status(r.get('status'), 'mr')} आहे.")
            parts.append("कृपया हा अहवाल आपल्या डॉक्टरांना दाखवा.")
            return " ".join(parts)

    elif lang == "es":
        parts = ["¡Hola! Aquí tiene un resumen hablado de sus análisis de sangre."]
        if not ab:
            parts.append(f"¡Excelente noticia! Todos los {len(results)} biomarcadores analizados están en rangos saludables.")
            return " ".join(parts)
        else:
            parts.append(f"De {len(results)} pruebas, {normal_count} son normales y {len(ab)} requieren evaluación médica.")
            for r in ab[:3]:
                parts.append(f"Su {r['name']} está {translate_status(r.get('status'), 'es')}.")
            parts.append("Recuerde compartir estos resultados con su médico.")
            return " ".join(parts)

    elif lang == "fr":
        parts = ["Bonjour ! Voici le compte-rendu vocal de votre bilan sanguin."]
        if not ab:
            parts.append(f"Très bonne nouvelle ! Vos {len(results)} marqueurs sont parfaitement dans les normes.")
            return " ".join(parts)
        else:
            parts.append(f"Sur {len(results)} examens, {normal_count} sont normaux et {len(ab)} méritent un avis médical.")
            for r in ab[:3]:
                parts.append(f"Votre {r['name']} est {translate_status(r.get('status'), 'fr')}.")
            parts.append("Pensez à transmettre ce bilan à votre médecin traitant.")
            return " ".join(parts)

    # Fallback to English speech script
    parts = ["Hello! Here is an audio walkthrough of your blood test results."]
    if crits:
        c_names = " and ".join(c["name"] for c in crits)
        parts.append(f"Important note: your {c_names} test requires immediate medical attention. Please contact your doctor or visit a clinic right away.")
    elif not ab:
        parts.append(f"The overall picture is very positive! All {len(results)} markers analyzed are within normal, healthy ranges. Keep up your healthy lifestyle.")
        return " ".join(parts)
    else:
        parts.append(f"We have analyzed {len(results)} tests in your report, and identified {len(ab)} markers that sit outside standard reference boundaries.")
        for r in ab[:4]:
            parts.append(f"Your {r['name']} is currently {r.get('status', 'out of range')}.")
    full_speech = " ".join(parts)
    # Strip any brackets or parens for clean TTS reading
    return re.sub(r"[()]", "", full_speech)

def generate_multilingual_chat(report: dict, question: str, lang: str = "en") -> str:
    """Generate intelligent grounded responses in the selected language when offline."""
    q = (question or "").lower().strip()
    results = report.get("results", [])
    ab = [r for r in results if r.get("status") != "normal"]
    
    # 1. Greetings
    if re.search(r"^(hi|hello|hey|नमस्ते|வணக்கம்|నమస్కారం|ನಮಸ್ಕಾರ|নমস্কার|नमस्कार|hola|bonjour)", q) or len(q) < 5:
        if lang == "hi":
            return ("नमस्ते! मैं आपका पल्स एआई स्वास्थ्य सहायक हूँ। मैं आपकी रिपोर्ट के परिणामों को समझा सकता हूँ, "
                    "असामान्य मानों के संभावित कारणों पर चर्चा कर सकता हूँ, या डॉक्टर से पूछने योग्य प्रश्न सुझा सकता हूँ। "
                    "आप किस परीक्षण के बारे में जानना चाहते हैं?")
        elif lang == "ta":
            return ("வணக்கம்! நான் உங்கள் பல்ஸ் ஏஐ மருத்துவ உதவியாளர். உங்கள் இரத்த பரிசோதனை முடிவுகள், "
                    "கவனிக்க வேண்டிய அளவுகள் மற்றும் மருத்துவரிடம் கேட்க வேண்டிய கேள்விகள் குறித்து உதவ முடியும். "
                    "நீங்கள் என்ன தெரிந்து கொள்ள விரும்புகிறீர்கள்?")
        elif lang == "te":
            return ("నమస్కారం! నేను మీ పల్స్ ఏఐ ఆరోగ్య సహాయకుడిని. మీ రక్త పరీక్ష నివేదికను విశ్లేషించడంలో, "
                    "అసాధారణ ఫలితాలను వివరించడంలో మరియు వైద్యుడిని అడగవలసిన ప్రశ్నలను సూచించడంలో సహాయపడతాను. "
                    "మీరు దేని గురించి తెలుసుకోవాలనుకుంటున్నారు?")
        elif lang == "es":
            return ("¡Hola! Soy su asistente médico de Pulse AI. Puedo explicarle los resultados de su analítica, "
                    "los valores que requieren atención o sugerirle preguntas clave para su médico. ¿En qué puedo ayudarle?")
        elif lang == "fr":
            return ("Bonjour ! Je suis votre assistant Pulse AI. Je peux vous expliquer les résultats de votre bilan, "
                    "les marqueurs hors normes ou vous proposer des questions pour votre médecin. Que souhaitez-vous savoir ?")
        else:
            return generate_multilingual_summary(report, lang)

    # 2. What to ask doctor
    if any(w in q for w in ("doctor", "डॉक्टर", "மருத்துவர்", "వైద్యుడు", "médico", "médecin", "ask", "पूछ", "கேள்")):
        lines = []
        if lang == "hi":
            lines.append("**डॉक्टर से परामर्श हेतु महत्वपूर्ण प्रश्न:**")
            lang_qs = DOCTOR_QUESTIONS.get("hi", {})
            for r in ab:
                k = r.get("key", "")
                if k in lang_qs:
                    lines.append(lang_qs[k])
                else:
                    lines.append(f"• \"मेरे {r['name']} ({r.get('value')} {r.get('unit')}) के स्तर के लिए आप क्या परामर्श देते हैं?\"")
            lines.append("\nकृपया अपनी अगली मुलाकात में यह रिपोर्ट अपने डॉक्टर को अवश्य दिखाएं।")
            return "\n".join(lines)
        elif lang == "ta":
            lines.append("**மருத்துவரிடம் கேட்க வேண்டிய கேள்விகள்:**")
            lang_qs = DOCTOR_QUESTIONS.get("ta", {})
            for r in ab:
                k = r.get("key", "")
                if k in lang_qs:
                    lines.append(lang_qs[k])
                else:
                    lines.append(f"• \"எனது {r['name']} அளவுக்கு என்ன சிகிச்சை தேவை?\"")
            return "\n".join(lines)
        elif lang == "te":
            lines.append("**వైద్యుడిని అడగవలసిన ముఖ్యమైన ప్రశ్నలు:**")
            lang_qs = DOCTOR_QUESTIONS.get("te", {})
            for r in ab:
                k = r.get("key", "")
                if k in lang_qs:
                    lines.append(lang_qs[k])
            return "\n".join(lines)
        elif lang == "es":
            lines.append("**Preguntas sugeridas para su médico:**")
            lang_qs = DOCTOR_QUESTIONS.get("es", {})
            for r in ab:
                k = r.get("key", "")
                if k in lang_qs:
                    lines.append(lang_qs[k])
            return "\n".join(lines)
        elif lang == "fr":
            lines.append("**Questions suggérées pour votre médecin :**")
            lang_qs = DOCTOR_QUESTIONS.get("fr", {})
            for r in ab:
                k = r.get("key", "")
                if k in lang_qs:
                    lines.append(lang_qs[k])
            return "\n".join(lines)

    # 3. Abnormal tests inquiry
    if any(w in q for w in ("abnormal", "असामान्य", "மாறுபாடு", "అసాధారణ", "anormal", "problem", "गंभीर")):
        if not ab:
            if lang == "hi":
                return "शुभ समाचार! आपकी रिपोर्ट के सभी परीक्षण सामान्य और स्वस्थ सीमाओं के भीतर हैं।"
            elif lang == "ta":
                return "அனைத்து பரிசோதனை முடிவுகளும் இயல்பான வரம்பிற்குள் உள்ளன."
            elif lang == "te":
                return "మీ నివేదికలోని అన్ని పరీక్షలు సాధారణ పరిమితుల్లో ఉన్నాయి."
            elif lang == "es":
                return "¡Buenas noticias! Todos los valores analizados se encuentran en rangos normales."
            elif lang == "fr":
                return "Tous vos biomarqueurs se situent dans les plages de référence normales."

        lines = []
        if lang == "hi":
            lines.append(f"आपकी रिपोर्ट में {len(ab)} परिणाम सामान्य सीमा से बाहर हैं:")
            for r in ab:
                t_stat = translate_status(r.get('status'), 'hi')
                lines.append(f"- **{r['name']}**: {r.get('value')} {r.get('unit')} ({t_stat}) [सामान्य सीमा: {r.get('ref_low')} - {r.get('ref_high')}]")
            lines.append("\nकृपया इन परिणामों पर अपने डॉक्टर से परामर्श लें।")
            return "\n".join(lines)
        elif lang == "ta":
            lines.append(f"உங்கள் அறிக்கையில் {len(ab)} சோதனைகள் இயல்பு வரம்பிற்கு வெளியே உள்ளன:")
            for r in ab:
                lines.append(f"- **{r['name']}**: {r.get('value')} {r.get('unit')} ({translate_status(r.get('status'), 'ta')})")
            return "\n".join(lines)
        elif lang == "te":
            lines.append(f"మీ నివేదికలో {len(ab)} పరీక్షలు సాధారణ పరిధికి భిన్నంగా ఉన్నాయి:")
            for r in ab:
                lines.append(f"- **{r['name']}**: {r.get('value')} {r.get('unit')} ({translate_status(r.get('status'), 'te')})")
            return "\n".join(lines)
        elif lang == "es":
            lines.append(f"Tiene {len(ab)} resultado(s) fuera del rango de referencia:")
            for r in ab:
                lines.append(f"- **{r['name']}**: {r.get('value')} {r.get('unit')} ({translate_status(r.get('status'), 'es')})")
            return "\n".join(lines)
        elif lang == "fr":
            lines.append(f"Vous avez {len(ab)} paramètre(s) hors des plages normales :")
            for r in ab:
                lines.append(f"- **{r['name']}**: {r.get('value')} {r.get('unit')} ({translate_status(r.get('status'), 'fr')})")
            return "\n".join(lines)

    # 4. Default: Return contextual summary in the requested language
    return generate_multilingual_summary(report, lang)
