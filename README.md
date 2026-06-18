Flow Academy Daily Gold Terminal V5.1

Fixes:
- Gold/Silver Ratio fallback. Tries XAUUSD/XAGUSD first, then GC=F/SI=F.
- Gold Momentum fallback. Tries XAUUSD first, then GC=F.
- Confidence score adjusted to a practical 55% to 95% range.
- Source Quality now shows the actual active source.

Deploy:
1. Upload app.py to GitHub replacing old app.py.
2. Upload requirements.txt replacing old requirements.txt.
3. Keep logo.png in the repository.
4. Reboot Streamlit app.
