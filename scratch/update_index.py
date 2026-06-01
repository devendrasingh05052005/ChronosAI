filepath = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace tab buttons block
old_buttons = """                            <div class="flex gap-1 bg-slate-200/60 p-1 rounded-xl shrink-0">
                                <button onclick="switchYearTab('all_years')" id="btn-year-all_years" class="year-tab-btn bg-slate-950 text-white px-4 py-2 rounded-lg text-xs font-bold shadow-sm transition-all duration-300">All Batches</button>
                                <button onclick="switchYearTab('2nd_year')" id="btn-year-2nd_year" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">2nd Year</button>
                                <button onclick="switchYearTab('3rd_year')" id="btn-year-3rd_year" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">3rd Year</button>
                                <button onclick="switchYearTab('4th_year')" id="btn-year-4th_year" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">4th Year</button>
                            </div>"""

new_buttons = """                            <div class="flex gap-1 bg-slate-200/60 p-1 rounded-xl shrink-0">
                                <button onclick="switchYearTab('all_years')" id="btn-year-all_years" class="year-tab-btn bg-slate-950 text-white px-4 py-2 rounded-lg text-xs font-bold shadow-sm transition-all duration-300">All Batches</button>
                                <button onclick="switchYearTab('2nd_year_a')" id="btn-year-2nd_year_a" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">2nd Year (Sec A)</button>
                                <button onclick="switchYearTab('2nd_year_b')" id="btn-year-2nd_year_b" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">2nd Year (Sec B)</button>
                                <button onclick="switchYearTab('3rd_year_a')" id="btn-year-3rd_year_a" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">3rd Year (Sec A)</button>
                                <button onclick="switchYearTab('3rd_year_b')" id="btn-year-3rd_year_b" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">3rd Year (Sec B)</button>
                                <button onclick="switchYearTab('4th_year')" id="btn-year-4th_year" class="year-tab-btn text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-300">4th Year</button>
                            </div>"""

# 2. Replace data-year attribute in row
old_data_year = 'data-year="{% if lecture.academic_year == \'2nd Year\' %}2nd_year{% elif lecture.academic_year == \'3rd Year\' %}3rd_year{% else %}4th_year{% endif %}"'
new_data_year = 'data-year="{% if lecture.academic_year == \'2nd Year\' %}2nd_year_{{ lecture.section|lower }}{% elif lecture.academic_year == \'3rd Year\' %}3rd_year_{{ lecture.section|lower }}{% else %}4th_year{% endif %}"'

if old_buttons in content:
    content = content.replace(old_buttons, new_buttons)
    print("SUCCESS: Tab buttons replaced!")
else:
    print("ERROR: Could not find old tab buttons block!")

if old_data_year in content:
    content = content.replace(old_data_year, new_data_year)
    print("SUCCESS: Row data-year replaced!")
else:
    print("ERROR: Could not find old data-year block!")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated index.html successfully!")
