import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import threading
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.client import OAuth2Credentials
import json
from tkinter import messagebox
from transliterate import translit

class StudentSurveyApp:
    def __init__(self, master, classes, json_file="survey_results.json", teacher_file="teacher_name.txt"):
        self.master = master
        self.master.title("Опитувальник для учнів")
        self.set_window_size(self.master, 900, 600)  # Встановлюємо стандартний розмір і центруємо
        self.classes = classes
        self.json_file = json_file
        self.teacher_file = teacher_file
        self.current_class = None
        self.students = []
        self.achievements = []
        self.current_student = 0
        self.teacher_name = self.load_teacher_name()
        self.results = {}

        # Фрейм для вибору класу
        self.class_frame = tk.Frame(master)
        self.class_frame.pack(padx=10, pady=10, fill="x")

        tk.Label(self.class_frame, text="Виберіть клас:", font=("Arial", 12)).pack(side="left", padx=5)
        self.class_combobox = ttk.Combobox(self.class_frame, values=list(self.classes.keys()), state="readonly")
        self.class_combobox.pack(side="left", padx=5)
        self.class_combobox.bind("<<ComboboxSelected>>", self.select_class)

        # Основний фрейм
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Заголовок учня і кнопка "Пропустити"
        self.header_frame = tk.Frame(self.main_frame)
        self.header_frame.pack(fill="x", pady=10)

        self.student_label = tk.Label(self.header_frame, text="", font=("Arial", 16), anchor="w")
        self.student_label.pack(side="left", padx=5)

        self.skip_button = tk.Button(self.header_frame, text="Пропустити", command=self.skip_student, state="disabled")
        self.skip_button.pack(side="left", padx=5)

        # Фрейм для скролу
        self.scroll_frame = tk.Frame(self.main_frame)
        self.scroll_frame.pack(fill="both", expand=True)

        # Canvas для скролу
        self.canvas = tk.Canvas(self.scroll_frame)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Скролбар
        self.scrollbar = tk.Scrollbar(self.scroll_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Внутрішній фрейм у Canvas
        self.characteristics_criteria_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.characteristics_criteria_frame, anchor="nw")

        # Додаємо подію для скролінгу колесом миші
        self.characteristics_criteria_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Кнопка "Далі"
        self.next_button = tk.Button(master, text="Далі", command=self.next_student, state="disabled")
        self.next_button.pack(pady=20)

    def set_window_size(self, window, width, height):
        """Встановлення розміру вікна і центрування."""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")  # Встановлюємо розмір і позицію

    def _on_mousewheel(self, event):
        """Скролінг колесом миші."""
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def load_teacher_name(self):
        """Завантажує ПІБ вчителя з файлу або запитує при першому запуску."""
        if os.path.exists(self.teacher_file):
            with open(self.teacher_file, "r", encoding="utf-8") as file:
                return file.read().strip()

        while True:
            teacher_name = simpledialog.askstring("ПІБ вчителя", "Введіть ваше прізвище:")
            if teacher_name:
                with open(self.teacher_file, "w", encoding="utf-8") as file:
                    file.write(teacher_name)
                return teacher_name
            else:
                messagebox.showerror("Помилка", "Введення обов'язкове! Будь ласка, введіть ваше прізвище.")

    def save_results(self):
        """Асинхронно зберігає результати, оновлюючи лише змінені дані."""
        # Виконуємо збереження у фоновому режимі
        threading.Thread(target=self._save_results_to_file).start()

    def _save_results_to_file(self):
        try:
            # Завантажуємо існуючі дані, якщо файл існує
            try:
                with open(self.json_file, "r", encoding="utf-8") as file:
                    existing_data = json.load(file)
            except FileNotFoundError:
                existing_data = {}

            # Оновлюємо дані
            for class_name, students in self.results.items():
                if class_name not in existing_data:
                    existing_data[class_name] = {}

                for student, achievements in students.items():
                    if student not in existing_data[class_name]:
                        existing_data[class_name][student] = {}

                    for achievement, value in achievements.items():
                        existing_data[class_name][student][achievement] = (
                            value.get() if isinstance(value, tk.StringVar) else value
                        )

            # Записуємо оновлені дані
            with open(self.json_file, "w", encoding="utf-8") as file:
                json.dump(existing_data, file, ensure_ascii=False, indent=4)

            self.upload_to_drive()  # Зберігаємо на Google Drive (опціонально)

        except Exception as e:
            print(f"Помилка збереження: {e}")

    def transliterate(text):
        """Транслітерація тексту з кирилиці в латиницю."""
        transliteration_table = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd',
            'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i',
            'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ь': '', 'ю': 'yu', 'я': 'ya', 'А': 'A', 'Б': 'B', 'В': 'V',
            'Г': 'H', 'Ґ': 'G', 'Д': 'D', 'Е': 'E', 'Є': 'Ye', 'Ж': 'Zh',
            'З': 'Z', 'И': 'Y', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K',
            'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
            'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
            'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ь': '', 'Ю': 'Yu', 'Я': 'Ya'
        }
        return ''.join(transliteration_table.get(c, c) for c in text)
    
    def upload_to_drive(self):
        """Завантажує результати на Google Диск."""
        try:
            # Транслітерація імені вчителя
            teacher_name_transliterated = translit(self.teacher_name, 'uk', reversed=True)
            file_name = f"{teacher_name_transliterated}.json"
            print(f"Transliterated file name: {file_name}")

            # Ваші дані облікових даних
            credentials_data = {
                "access_token": "ya29.a0ARW5m755isDdme8FMIVjQfSOMjDph8N7zwsqkYf8Xpt89h7VOppQO5ru1SJchPgy8JqrVq2iWeu_Nm5yjjBQSmGPXUqYU_AMu8AY6kDcvUQDcgsVfaa3gI-sS04USLCIU97ZH4K19F8Tf7hvoLRohGub58AaQa83D8aEzK4QaCgYKASESARASFQHGX2MicafDap0MOVFnSzz7jrZJLg0175",
                "client_id": "17131118338-r7la4lq5lsfk7mjdsif9hei8rp0hg49n.apps.googleusercontent.com",
                "client_secret": "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",
                "refresh_token": "1//09YDYZhKwWzjACgYIARAAGAkSNwF-L9Irb0SubAUf1PQI4phTj6_vcX0B-PGKeBKZpM5Iajj5XZmHqm2C7iAvCDs5mT9eSR8za1k",
                "token_expiry": "2024-12-23T12:46:27.144892",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": [
                    "https://www.googleapis.com/auth/drive"
                ]
            }

            # Конвертуємо JSON в об'єкт OAuth2Credentials
            credentials = OAuth2Credentials(
                access_token=credentials_data["access_token"],
                client_id=credentials_data["client_id"],
                client_secret=credentials_data["client_secret"],
                refresh_token=credentials_data["refresh_token"],
                token_expiry=None,
                token_uri=credentials_data["token_uri"],
                user_agent=None,
                scopes=credentials_data["scopes"]
            )

            # Передаємо облікові дані в GoogleAuth
            gauth = GoogleAuth()
            gauth.credentials = credentials

            # Підключаємо Google Drive
            drive = GoogleDrive(gauth)

            # Шукаємо існуючий файл у конкретній папці
            folder_id = "1IqNguQSWJK6cWLgZZpsls8kch9pS7ewt"  # Замініть на ID вашої папки
            query = f"'{folder_id}' in parents and title contains '{teacher_name_transliterated}'"
            file_list = drive.ListFile({'q': query}).GetList()
            if file_list:
                file = file_list[0]
                print("Existing file found")
            else:
                file_metadata = {
                    "title": file_name,
                    "parents": [{"id": folder_id}]
                }
                file = drive.CreateFile(file_metadata)
                print("New file created")

            file.SetContentFile(self.json_file)
            file.Upload()
            print("File uploaded successfully")

        except Exception as e:
            print(f"Помилка завантаження на Google Диск: {e}")
            messagebox.showerror("Помилка", f"Помилка завантаження на Google Диск: {e}")

    def select_class(self, event):
        """Завантажує учнів і характеристики для вибраного класу."""
        self.current_class = self.class_combobox.get()
        self.students, self.achievements = self.classes[self.current_class]
        self.current_student = 0
        if self.current_class not in self.results:
            self.results[self.current_class] = {student: {} for student in self.students}
        self.show_student()
        self.next_button.config(state="normal")
        self.skip_button.config(state="normal")

    def show_student(self):
        """Відображає дані поточного учня."""
        if self.current_student < len(self.students):
            student = self.students[self.current_student]
            self.student_label.config(text=f"Учень: {student}")

            # Очищуємо попередні елементи
            for widget in self.characteristics_criteria_frame.winfo_children():
                widget.destroy()

            # Кнопки для автоматичного вибору всіх критеріїв
            button_frame = tk.Frame(self.characteristics_criteria_frame)
            button_frame.pack(anchor="w", pady=10)

            tk.Button(
                button_frame, text="Вибрати всі: Має значні успіхи", 
                command=lambda: self.set_all_criteria("Має значні успіхи")
            ).pack(side="left", padx=5)

            tk.Button(
                button_frame, text="Вибрати всі: Демонструє помітний прогрес", 
                command=lambda: self.set_all_criteria("Демонструє помітний прогрес")
            ).pack(side="left", padx=5)

            tk.Button(
                button_frame, text="Вибрати всі: Потребує уваги і допомоги", 
                command=lambda: self.set_all_criteria("Потребує уваги і допомоги")
            ).pack(side="left", padx=5)

            # Відображаємо характеристики і критерії
            for achievement in self.achievements:
                row_frame = tk.Frame(self.characteristics_criteria_frame)
                row_frame.pack(fill="x", pady=5)

                tk.Label(row_frame, text=achievement, anchor="w", width=40, wraplength=280, justify="left").pack(side="left", padx=5)

                # Ініціалізація результату, якщо його ще немає
                if achievement not in self.results[self.current_class][student]:
                    self.results[self.current_class][student][achievement] = tk.StringVar(value="")

                selected_value = self.results[self.current_class][student][achievement]

                for option in ["Має значні успіхи", "Демонструє помітний прогрес", "Потребує уваги і допомоги"]:
                    ttk.Radiobutton(row_frame, text=option, variable=selected_value, value=option).pack(side="left", padx=5)
        else:
            self.finish_survey()
    
    def set_all_criteria(self, value):
        """Встановлює однакове значення для всіх критеріїв."""
        student = self.students[self.current_student]
        for achievement in self.achievements:
            self.results[self.current_class][student][achievement].set(value)

    def next_student(self):
        """Зберігає вибір і переходить до наступного учня."""
        student = self.students[self.current_student]
        for achievement, var in self.results[self.current_class][student].items():
            if not var.get():
                messagebox.showwarning("Попередження", f"Виберіть усі критерії для {achievement}.")
                return
        self.current_student += 1
        self.show_student()

    def skip_student(self):
        """Пропускає поточного учня і переходить до наступного."""
        self.current_student += 1
        self.show_student()

    def finish_survey(self):
        """Завершує опитування."""
        messagebox.showinfo("Готово", f"Результати для класу {self.current_class} збережено. Оберіть наступний клас або закрийте програму.")
        self.save_results()
        self.current_class = None
        self.class_combobox.set("")
        self.next_button.config(state="disabled")
        self.skip_button.config(state="disabled")


# Дані про класи, учнів і характеристики
classes = {
    "5-А": (["Биба Влада", "Білозьоров Юрій", "Бурда Уляна", "Веремеєнко Віталій", "Версітілов Кирил", "Гоцалюк Тимофій", "Ель Хакім Олександр", "Коваленко Максим", "Коваль Гордій", "Ковальчук Нікіта", "Майстренко Артем", "Максименко Майя", "Мірюк Анастасія", "Мовчан Ніка", "Піха Лука", "Плачинда Дмитро", "Ремез Олександр", "Сеньків Ангеліна", "Сеньків Афіна", "Сипало Діана", "Сідько Владислав", "Соколан Ярослав", "Чередник Віра", "Черних Артем"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "5-Б": (["Браташов Тимофій", "Вердзадзе Лука", "Гарбуль Софія", "Гринишина Соломія", "Ігнатуха Макар", "Ільчевська Вікторія", "Кононович Ярослав", "Копачовець Варвара", "Лемещук Іван", "Логозинський Данііл", "Лупащенко Єлизавета", "Маліновський Вадим", "Редун Олександра", "Соломко Христина", "Торгало Варвара", "Фальковський Микита", "Чабаненко Валерія", "Чоларія Міхаіл", "Шапран Вероніка"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "5-В": (["Антух Валерія", "Астаф'єв Андрій", "Гурська Дарина", "Єрмоличева Дарина", "Коваль Поліна", "Корнійчук Дмитро", "Кретова Маргарита", "Крилов Єлисей", "Лукашевич Михайло", "Михайленко Даніїл", "Мухіна Юлія Денисівна", "Назаркова Олександра", "Немчинов Дмитро", "Опалєва Вероніка", "Панкова Софья", "Панькова Юлія", "Поляковська Тетяна", "Салій Серафим", "Смірнов Андрій", "Смолій Ніка", "Солярик Ірина", "Стеценко Єлизавета", "Церетелі Самсон", "Цимбалюк Богдан", "Чумачов Андрій", "Школяренко Карина"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "6-А": (["Амеліна Вероніка", "Андріяка Аліса", "Бондаренко Марія", "Гарник Вікторія", "Данильчик Кіріл", "Демчук Єлизавета", "Демчук Марія", "Домрес Роман", "Єгоров Михайло", "Єрмолко Мірослава", "Жеребнюк Костянтин", "Загоруй Софія", "Кисельова Єва", "Кіктенко Нікіта", "Ладнай Лев", "Морозов Микола", "Поліщук Аліса", "Приходько Леонід", "Рисман Еліна", "Рябуха Ілля", "Слободян Богдана", "Солонін Глєб", "Уманський Євген", "Хардікова Кіра", "Циганенко Дмитро", "Шибкой Матвій", "Шифоєва Карина"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "6-Б": (["Авдєєнко Дмитро", "Бабенко Макар", "Баблакова Марія", "Білоусов Матвєй", "Візір Ярослав", "Гнатенко Дмитро", "Головіна Єлизавета", "Губко Марія", "Драшко Таїсія", "Ємельянов Володимир", "Зінчук Андрій", "Кучинська Анна", "Левченко Евеліна", "Ліцман Софія", "Лукашов Олександр", "Носовська Віра", "Обухов Тимофій", "Півень Нікіта", "Прянішнікова Анастасія", "Романенко Кирил", "Сахарук Назар", "Сосула Назар", "Товмасян Ася", "Тридуб Кіра", "Фролов Єлисей", "Черевко Аліса", "Шелудько Іван"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "6-В": (["Гаспарян Олександр", "Дишкант Єгор", "Каляєв Ян", "Кобилінська Вероніка", "Любцов-Ткачук Назар", "Нікітін Мирослав", "Паламарчук Олександр", "Савченко Софія", "Сиверський Назарій", "Шпера Михайло", "Штанько Варвара"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "7-А": (["Александров Дмитро", "Биба Макар", "Буковчаник Поліна", "Вірич Ярослава", "Галієва Анелія", "Глазков Георгій", "Горєв Олександр", "Дем'янець Дмитро", "Іващенко Олексій", "Кагадій Софія", "Корнієнко Валерія", "Костюк Євгеній", "Круглікова Аліна Софія", "Кухта Юліан", "Лисько Дар'я", "Матвєєв Нікіта", "Мелашенко Ілля", "Мойсюк Богдана", "Моргунова Вероніка", "Оверченко Ростислав", "Оцалюк Варвара", "Половинка Анна", "Протасевич Кирило", "Романенко Христина", "Савицький Денис", "Самойлик Анастасія", "Сідько Вероніка", "Скібнєва Софія", "Смірнова Марія", "Ткаченко Єгор", "Урбанський Віктор", "Федоренко Тимур", "Хрустальова Ірина", "Шевченко Кирило", "Шугайлюк Ілля"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "7-Б": (["Баблакова Ксенія", "Бебешко Марія", "Бєлунічева Ніка", "Бойко Кіра", "Бондар Христина", "Брідун Ярослав", "Вайзер Дмитро", "Васянович Наталія", "Войтишін Єгор", "Гайович Крістіна", "Грозна Юлія", "Довгань Максим", "Збаратська Анастасія", "Зінченко Катерина", "Коз'яков Захар", "Мазурок Гліб", "Мороз Каміла", "Онопрійко Поліна", "Патик Віра", "Поплавська Єва", "Прилепова Софья", "Рибальченко Єгор", "Романенко Анастасія", "Сарнавський Владислав", "Седнівець Олександра", "Сергеєнко Денис", "Скок Владислав", "Ткачук Артур", "Федоряка Єва", "Фомін Олексій", "Шемлей Тимур"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"]),
    "7-В": (["Біляк Богдана", "Брухаль Соломія", "Величко Микита", "Горянський Філіп", "Гроссман Ілля", "Губа Ольга", "Животенко Марія", "Забронська Дар'я", "Каленська Марія", "Коржов Тимофій", "Корінь Лев", "Магдій Діана", "Маковеєва Софія", "Миненко Анастасія", "Омельченко Анастасія", "Орєхов Демид", "Панасюк Ніна", "Семенюк Макар"], ["сприймає та усвідомлює прочитане", "висловлює припущення, доводить надійність аргументів", "висловлює ідеї, пов’язані з розумінням тексту, аналізує текст і добирає контраргументи (за потреби)", "передає власні думки, почуття, переконання", "зважає на мету та учасників комунікації", "вибирає для цього відповідні мовленнєві стратегії", "визначає характерні ознаки явищ, подій, ідей, їх взаємозв’язків", "уміє аналізувати та оцінювати доказовість і вагомість аргументів у судженнях", "уміє розрізняти факти, розпізнавати спроби маніпулювання даними", "висловлює послідовні, обґрунтовані міркування у вигляді суджень і висновків", "вибирає завдання, які є викликом для нього/неї, новою діяльністю", "використовує знання з різних предметів і галузей знань для створення нових ідей", "використовує різноманітні стратегії для продукування нових ідей", "пропонує власні рішення для розв’язання проблем", "уміє брати на себе відповідальність", "розпізнає власні емоції та емоційний стан інших", "сприймає емоції без осуду, адекватно реагує на конфліктні ситуації", "розуміє, як емоції можуть допомагати і заважати в діяльності", "розрізняє ризики та загрози", "шукає способи прийняття рішень в умовах неповної інформації", "розпізнає проблемні ситуації і висловлює припущення щодо їх розв’язання", "обирає способи розв’язання проблемних ситуацій на основі розуміння причин та обставин, які призводять до їх виникнення", "аналізує проблемні ситуації, формулює проблеми, висуває гіпотези", "уміє практично їх перевірити та обґрунтовувати", "презентує та аргументує рішення", "планує власну та групову роботу", "підтримує учасників групи, допомагає іншим і заохочує їх до досягнення спільної мети"])
}

# Створення вікна програми
root = tk.Tk()
app = StudentSurveyApp(root, classes)
root.mainloop()