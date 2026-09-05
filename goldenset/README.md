Golden set — the answer key for transcription accuracy
======================================================

Kyun chahiye: Sarvam lagane ke baad "behtar lag raha hai" ek feeling hai,
proof nahi. Ye folder proof hai. Same 20-30 clips dono engines me daal ke
number nikalta hai — kitne percent shabd sahi aaye. Capstone me yahi
number dikhana hai, screenshot nahi.

Kya karna hai
-------------
1. `clips/` folder me chhoti recordings daalo. Har clip 5-15 second.
   Phone ke voice recorder se bhi chalega.

2. Naam is tarah rakho — `<number>_<bhasha>.wav` (ya .m4a / .mp3):

       01_gu.wav      poori Gujarati
       02_hi.wav      poori Hindi
       03_en.wav      poori English
       04_mix.wav     mila-jula (jaise "login OTP se hona chahiye, admin
                      panel ma badha users dekhai")

   Kitne: 8 Gujarati, 8 Hindi, 6 English, 8 mix. Total 30 ke aaspaas.

3. Har clip me aisi baat bolo jo asli client meeting me boli jaati hai —
   feature ki demand, screen ka zikr, payment, login, report. Kavita ya
   random baatein mat bolo, unse pata nahi chalta ki project ke kaam ke
   liye engine sahi hai ya nahi.

4. `reference.csv` me har clip ke saamne likho ki **actual kya bola** —
   bilkul jaisa bola, apne aap theek kiye bina. Ye hi answer key hai.
   Agar clip Hindi/Gujarati me hai to `english` column me uska sahi
   English matlab bhi likh do (translation bhi check karna hai).

5. 2-3 clips shor me record karo (fan chalu, thoda door se bolo) aur
   unke naam ke aage `_noisy` laga do — asli meeting saaf studio nahi
   hoti, aur yahi clips sabse zyada fail hote hain.

Baaki main karunga
------------------
Ho gaya — `backend/scripts/accuracy_benchmark.py` likh diya hai. Clips
daalke, `reference.csv` bharke, backend folder se ye chalao:

    python scripts/accuracy_benchmark.py

Har clip ka per-clip aur per-language word-error-rate (WER) aur time print
karega, phir overall summary. `-v` / `--verbose` lagao to har clip ke liye
engine ne asal me kya suna wo bhi dikhega — expected text ke saamne.

Note: audio files git me nahi jaayengi (bahut badi hoti hain, aur is
folder me `.gitignore` hai) — sirf `reference.csv` track hoti hai. 