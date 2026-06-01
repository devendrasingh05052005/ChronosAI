import os

html_path = r"c:\Users\jmsin\Desktop\chronosai\scheduler_api\templates\index.html"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

target_str = """                                                     <div class="flex items-center gap-2 flex-wrap">
                                                         <span class="bg-slate-950 text-white font-mono text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase">{{ lecture.day_of_week }}</span>
                                                         <span class="bg-orange-100 text-orange-900 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider font-extrabold">{{ lecture.academic_year }} (Sec {{ lecture.section }})</span>
                                                         <span class="bg-slate-100 text-slate-600 text-[9px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider font-semibold"><i class="fa-solid fa-map-pin mr-1 text-slate-400"></i>{{ lecture.room_number|default:"Room 302" }}</span>
                                                     </div>"""

replacement_str = """                                                     <div class="flex items-center gap-2 flex-wrap">
                                                         <span class="bg-slate-950 text-white font-mono text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase">{{ lecture.day_of_week }}</span>
                                                         <span class="bg-orange-100 text-orange-900 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider font-extrabold">{{ lecture.academic_year }} (Sec {{ lecture.section }})</span>
                                                         <span class="bg-slate-100 text-slate-600 text-[9px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider font-semibold"><i class="fa-solid fa-map-pin mr-1 text-slate-400"></i>{{ lecture.room_number|default:"Room 302" }}</span>
                                                         {% if lecture.is_proxy %}
                                                         <span class="bg-rose-100 text-rose-800 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider font-extrabold animate-pulse"><i class="fa-solid fa-user-shield mr-1"></i>Proxy (For: {{ lecture.employee.name }})</span>
                                                         {% endif %}
                                                     </div>"""

if target_str in content:
    new_content = content.replace(target_str, replacement_str)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESS: Proxy badge successfully added to index.html!")
else:
    # Try with unix line endings or check whitespace
    print("WARNING: Target string not found directly. Attempting normalized replacement...")
    # Replace using a regex or split lines
    lines = content.splitlines()
    found = False
    for idx, line in enumerate(lines):
        if 'lecture.room_number|default:"Room 302"' in line and 'flex-wrap' in lines[idx-3]:
            # This is the block!
            lines.insert(idx + 1, '                                                         {% if lecture.is_proxy %}')
            lines.insert(idx + 2, '                                                         <span class="bg-rose-100 text-rose-800 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider font-extrabold animate-pulse"><i class="fa-solid fa-user-shield mr-1"></i>Proxy (For: {{ lecture.employee.name }})</span>')
            lines.insert(idx + 3, '                                                         {% endif %}')
            found = True
            break
    if found:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("SUCCESS: Normalized proxy badge replacement complete!")
    else:
        print("FAILED: Could not locate the target block inside index.html.")
