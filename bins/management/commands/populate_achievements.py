from django.core.management.base import BaseCommand
from bins.models import Achievement

class Command(BaseCommand):
    help = "Populate initial achievements"

    def handle(self, *args, **options):
        achievements = [
            # Consistency Badges
            {
                'name': 'First Step',
                'description': 'Report your first waste bin',
                'category': 'CONSISTENCY',
                'points_reward': 10,
                'requirement': 'Report 1 bin',
                'condition_value': 1,
            },
            {
                'name': 'Dedicated User',
                'description': 'Maintain a 7-day streak',
                'category': 'CONSISTENCY',
                'points_reward': 50,
                'requirement': 'Maintain 7 consecutive days',
                'condition_value': 7,
            },
            {
                'name': 'Weekly Champion',
                'description': 'Maintain a 30-day streak',
                'category': 'CONSISTENCY',
                'points_reward': 150,
                'requirement': 'Maintain 30 consecutive days',
                'condition_value': 30,
            },
            # Reporting Badges
            {
                'name': 'Eagle Eye',
                'description': 'Report 5 waste bins',
                'category': 'REPORTING',
                'points_reward': 30,
                'requirement': 'Report 5 bins',
                'condition_value': 5,
            },
            {
                'name': 'Super Reporter',
                'description': 'Report 25 waste bins',
                'category': 'REPORTING',
                'points_reward': 100,
                'requirement': 'Report 25 bins',
                'condition_value': 25,
            },
            {
                'name': 'Environmental Hero',
                'description': 'Report 100 waste bins',
                'category': 'REPORTING',
                'points_reward': 300,
                'requirement': 'Report 100 bins',
                'condition_value': 100,
            },
            # Community Badges
            {
                'name': 'Community Starter',
                'description': 'Help 1 user',
                'category': 'COMMUNITY',
                'points_reward': 20,
                'requirement': 'Help 1 community member',
                'condition_value': 1,
            },
            {
                'name': 'Community Builder',
                'description': 'Help 10 users',
                'category': 'COMMUNITY',
                'points_reward': 75,
                'requirement': 'Help 10 community members',
                'condition_value': 10,
            },
            # Exploration Badges
            {
                'name': 'Explorer',
                'description': 'Visit 5 different bin locations',
                'category': 'EXPLORATION',
                'points_reward': 40,
                'requirement': 'Visit 5 locations',
                'condition_value': 5,
            },
            {
                'name': 'Map Master',
                'description': 'Visit 20 different bin locations',
                'category': 'EXPLORATION',
                'points_reward': 120,
                'requirement': 'Visit 20 locations',
                'condition_value': 20,
            },
            # Milestone Badges
            {
                'name': '1000 Points Club',
                'description': 'Reach 1000 total points',
                'category': 'MILESTONE',
                'points_reward': 100,
                'requirement': 'Earn 1000 points',
                'condition_value': 1000,
            },
        ]

        for achievement_data in achievements:
            achievement, created = Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults=achievement_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created achievement: {achievement.name}"))
            else:
                self.stdout.write(f"Achievement already exists: {achievement.name}")

        self.stdout.write(self.style.SUCCESS("Successfully populated achievements"))