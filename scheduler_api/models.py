from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=255, unique=True)
    department = models.CharField(max_length=50, default='CSE-AIDS')

    class Meta:
        ordering = ['name']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        return self.name


class TimetableFile(models.Model):
    file = models.FileField(upload_to='timetables/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Timetable File'
        verbose_name_plural = 'Timetable Files'

    def __str__(self):
        return f"Timetable uploaded at {self.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}"


from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('HOD', 'HOD'),
        ('Faculty', 'Faculty'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Faculty')
    employee = models.OneToOneField(Employee, on_delete=models.SET_NULL, blank=True, null=True, related_name='user_profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} | {self.role}"


class Schedule(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    
    YEAR_CHOICES = [
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]
    
    SEM_CHOICES = [
        (4, 4),
        (6, 6),
        (8, 8),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.CharField(max_length=20)
    end_time = models.CharField(max_length=20)
    task_name = models.CharField(max_length=255)
    is_proxy = models.BooleanField(default=False)
    proxy_teacher_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Phase 3 upgrades for multiple batches
    academic_year = models.CharField(max_length=20, choices=YEAR_CHOICES, default='3rd Year')
    semester = models.IntegerField(choices=SEM_CHOICES, default=6)
    section = models.CharField(max_length=10, default='A')
    room_number = models.CharField(max_length=50, blank=True, null=True, default='Room 302')
    department = models.CharField(max_length=50, default='CSE-AIDS')

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Schedule Entry'
        verbose_name_plural = 'Schedule Entries'

    def __str__(self):
        proxy_info = f" [PROXY: {self.proxy_teacher_name}]" if self.is_proxy else ""
        return (
            f"[{self.academic_year} Sec {self.section}] {self.employee.name} | {self.day_of_week} | "
            f"{self.start_time}-{self.end_time} | {self.task_name}{proxy_info}"
        )


class SyllabusLog(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='syllabus_logs')
    date = models.DateField(auto_now_add=True)
    topic_covered = models.TextField()
    logged_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='syllabus_logs')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.logged_by.name} | {self.schedule.task_name} | {self.date}"


class SwapRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    requestor = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sent_swap_requests')
    target_teacher = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='received_swap_requests')
    schedule_slot = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='swap_requestor_slots')
    target_slot = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='swap_target_slots')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.requestor.name} <-> {self.target_teacher.name} | {self.status}"
