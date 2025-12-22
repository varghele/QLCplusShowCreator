# Questions for User

## Sublane Test Running

A test window should be open on your screen showing the sublane rendering test.

### What You Should See in the Test Window

The window displays 3 test lanes:

1. **Moving Head Lane**
   - Height: **240px** (4 sublanes × 60px)
   - Should show 3 horizontal dashed lines separating 4 sublanes
   - Expected capabilities: Dimmer, Colour, Movement, Special

2. **RGBW Par Lane**
   - Height: **120px** (2 sublanes × 60px)
   - Should show 1 horizontal dashed line separating 2 sublanes
   - Expected capabilities: Dimmer, Colour (no Movement or Special)

3. **Simple Fixture Lane**
   - Height varies based on fixture definition
   - May show different number of sublanes

### What to Check

Look for these visual elements:
- ✅ Lane heights are **different** based on fixture type
- ✅ **Horizontal dashed separator lines** are visible between sublanes
- ✅ **Capability detection info** below each lane shows correct values
- ✅ Grid lines (vertical) still visible in background
- ✅ Each lane has control buttons on the left side

---

## QUESTIONS

Please close the test window when done reviewing, then answer:

### Question 1: Does the test look correct?
- Are the lane heights different (240px vs 120px)?
- Anwer: Yes they are different
- Can you see the horizontal dashed lines separating sublanes?
- Answer: Yes I can see them.
- Does the capability info text match expectations?
- Answer: Yes, currently it matches expectations.

**Answer: YES / NO / Issues:**

---

### Question 2: Any issues or unexpected behavior?
- Missing separator lines?
- Answer: Not that I can see
- Wrong heights?
- Answer: THe last line seems to be quite squished
- Errors in console?
- Other visual problems?

**Answer:**

---

### Question 3: Ready to continue?
Once the test looks good, should I proceed with:
- **Option A**: Continue with LightBlockWidget modifications (Step 4)
- **Option B**: Fix any issues you found
- Let's go with option B: fixing the issues first.
- **Option C**: Something else

**Answer: A / B / C**

---

**Please respond by updating this file or just tell me directly in chat!**
