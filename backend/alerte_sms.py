"""
PhytoGuard-Pi | alerte_sms.py
Membre C | Semaine 4

Envoie une alerte SMS via Twilio quand le niveau BBCH est critique (niveau 4).
"""

from twilio.rest import Client

# ─────────────────────────────────────────────
# Configuration Twilio
# ─────────────────────────────────────────────
ACCOUNT_SID   = "VOTRE_ACCOUNT_SID"
AUTH_TOKEN    = "VOTRE_AUTH_TOKEN"
TWILIO_NUMBER = "VOTRE_NUMERO_TWILIO"
MON_NUMERO    = "VOTRE_NUMERO_PERSONNEL"
# ─────────────────────────────────────────────
# Fonction d'envoi SMS
# ─────────────────────────────────────────────
def envoyer_alerte_sms(maladie, culture, severite, surface, parcelle_id=None):
    labels = {0: "Sain", 1: "Léger", 2: "Modéré", 3: "Sévère", 4: "ÉPIDÉMIQUE"}
    label  = labels.get(severite, "Inconnu")
    parcelle_info = f"Parcelle #{parcelle_id}" if parcelle_id else "Parcelle non spécifiée"
    message = (
        f"🚨 ALERTE PhytoGuard-Pi\n"
        f"Maladie : {maladie.capitalize()}\n"
        f"Culture : {culture.capitalize()}\n"
        f"Sévérité : {label} (BBCH {severite}/4)\n"
        f"Surface atteinte : {surface}%\n"
        f"{parcelle_info}\n"
        f"⚠️ Traitement d'urgence requis !"
    )
    
    # Affichage terminal toujours
    print("\n" + "="*50)
    print(message)
    print("="*50 + "\n")
    
    # SMS Twilio si credentials disponibles
    if ACCOUNT_SID == "VOTRE_ACCOUNT_SID":
        print("[INFO] Credentials Twilio non configurés — SMS non envoyé")
        return False
    
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=MON_NUMERO
        )
        print(f"[OK] SMS envoyé ! SID : {msg.sid}")
        return True
    except Exception as e:
        print(f"[ERREUR] SMS non envoyé : {e}")
        return False

# ─────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🧪 Test d'envoi SMS Twilio...\n")
    envoyer_alerte_sms(
        maladie     = "mildiou",
        culture     = "tomate",
        severite    = 4,
        surface     = 65.0,
        parcelle_id = 1
    )