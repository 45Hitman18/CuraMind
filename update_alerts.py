import os
import re

toast_html = """{% if messages %}
<div id="toast-container" class="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
    {% for message in messages %}
    <div class="toast-message pointer-events-auto flex items-start gap-4 px-5 py-4 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border border-slate-200/50 dark:border-slate-700/50 shadow-2xl shadow-slate-900/10 rounded-[1.5rem] max-w-[360px] transform transition-all duration-700 hover:scale-105 translate-y-12 opacity-0" role="alert">
        {% if 'success' in message.tags %}
        <div class="w-10 h-10 rounded-full bg-primary text-slate-900 flex items-center justify-center shrink-0 shadow-lg shadow-primary/30">
            <span class="material-symbols-outlined text-[20px] font-bold">check_circle</span>
        </div>
        <div class="flex-1 mt-0.5 min-w-0">
            <h4 class="text-[14px] font-black text-slate-900 dark:text-white leading-tight">Success</h4>
            <p class="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">{{ message }}</p>
        </div>
        {% elif 'error' in message.tags or 'danger' in message.tags %}
        <div class="w-10 h-10 rounded-full bg-rose-500 text-white flex items-center justify-center shrink-0 shadow-lg shadow-rose-500/30">
            <span class="material-symbols-outlined text-[20px] font-bold">error</span>
        </div>
        <div class="flex-1 mt-0.5 min-w-0">
            <h4 class="text-[14px] font-black text-slate-900 dark:text-white leading-tight">Action Failed</h4>
            <p class="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">{{ message }}</p>
        </div>
        {% else %}
        <div class="w-10 h-10 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center shrink-0 shadow-lg shadow-black/10">
            <span class="material-symbols-outlined text-[20px] font-bold">notifications</span>
        </div>
        <div class="flex-1 mt-0.5 min-w-0">
            <h4 class="text-[14px] font-black text-slate-900 dark:text-white leading-tight">Update</h4>
            <p class="text-[12px] font-medium text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">{{ message }}</p>
        </div>
        {% endif %}
        <button class="text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 w-7 h-7 rounded-full flex items-center justify-center" onclick="this.closest('.toast-message').remove()">
            <span class="material-symbols-outlined text-[16px]">close</span>
        </button>
    </div>
    {% endfor %}
</div>
<script>
    document.addEventListener('DOMContentLoaded', () => {
        const toasts = document.querySelectorAll('.toast-message');
        toasts.forEach((toast, index) => {
            // Animate in
            setTimeout(() => {
                toast.classList.remove('translate-y-12', 'opacity-0');
            }, index * 120 + 10);
            
            // Animate out automatically after 5 sec
            setTimeout(() => {
                toast.classList.add('opacity-0', 'scale-95');
                setTimeout(() => toast.remove(), 700);
            }, 5000 + (index * 800));
        });
    });
</script>
{% endif %}"""

template_dir = r"c:\Users\thaka\OneDrive\Desktop\curaMind\templates"
for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex to find and replace the block
            # This is robust because we know the exact structure of the old {% if messages %} blocks used across the site
            pattern = re.compile(r'{%\s*if messages\s*%}.*?{%\s*endif\s*%}', re.DOTALL)
            new_content, count = pattern.subn(toast_html, content)
            
            if count > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {file}")

print("Complete.")
