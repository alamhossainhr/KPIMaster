from decimal import Decimal
from django.db.models import Sum, Avg
from .models import KPIAssignment, DailyWork, WorkApproval, MonthlyKPI, PerformanceReview, RatingScale

class KPICalculationEngine:
    @staticmethod
    def validate_employee_kpi_weight(employee, period):
        """Validates that assigned KPI weights equal exactly 100%."""
        total_weight = KPIAssignment.objects.filter(
            employee=employee, period=period
        ).aggregate(total=Sum('weight'))['total'] or Decimal('0.0')
        return total_weight == Decimal('100.0'), total_weight

    @staticmethod
    def calculate_monthly_kpi(employee, period):
        """Aggregates all verified and approved daily work into monthly KPI achievements."""
        assignments = KPIAssignment.objects.filter(employee=employee, period=period)
        total_system_weighted_score = Decimal('0.0')

        for assign in assignments:
            # Get all approved daily work entries for this KPI in the given period date range
            approved_entries = DailyWork.objects.filter(
                employee=employee,
                kpi=assign.kpi,
                work_date__range=(period.start_date, period.end_date),
                status__in=['Approved', 'Partially Approved']
            )

            total_target = approved_entries.aggregate(Sum('target_quantity'))['target_quantity__sum'] or Decimal('0.0')
            total_verified = Decimal('0.0')
            avg_quality = Decimal('0.0')
            avg_timeliness = Decimal('0.0')
            avg_sup = Decimal('0.0')

            count = approved_entries.count()
            if count > 0:
                approvals = WorkApproval.objects.filter(daily_work__in=approved_entries)
                total_verified = approvals.aggregate(Sum('verified_achievement'))['verified_achievement__sum'] or Decimal('0.0')
                avg_quality = approvals.aggregate(Avg('quality_score'))['quality_score__avg'] or Decimal('0.0')
                avg_timeliness = approvals.aggregate(Avg('timeliness_score'))['timeliness_score__avg'] or Decimal('0.0')
                avg_sup = approvals.aggregate(Avg('supervisor_score'))['supervisor_score__avg'] or Decimal('0.0')

            # Calculate achievement percentage
            if total_target > 0:
                achievement_pct = min(Decimal('100.0'), (Decimal(str(total_verified)) / Decimal(str(total_target))) * Decimal('100.0'))
            else:
                achievement_pct = Decimal('100.0') if total_verified > 0 else Decimal('0.0')

            # Weighted KPI score: (Achievement % * Weight) / 100
            weighted_score = (achievement_pct * Decimal(str(assign.weight))) / Decimal('100.0')
            total_system_weighted_score += weighted_score

            MonthlyKPI.objects.update_or_create(
                employee=employee,
                period=period,
                kpi=assign.kpi,
                defaults={
                    'weight': assign.weight,
                    'total_target': total_target,
                    'total_verified_achievement': total_verified,
                    'achievement_percentage': achievement_pct,
                    'average_quality_score': avg_quality,
                    'average_timeliness_score': avg_timeliness,
                    'average_supervisor_score': avg_sup,
                    'weighted_score': weighted_score,
                    'final_kpi_score': weighted_score,
                }
            )

        # Performance Review Calculation: System (80%) + Supervisor Evaluation (20%)
        review, _ = PerformanceReview.objects.get_or_create(
            employee=employee, period=period
        )
        if not review.is_overridden:
            review.system_generated_score = total_system_weighted_score
            # Default supervisor evaluation score matches system score if not manually graded yet
            if review.supervisor_evaluation_score == Decimal('0.0'):
                review.supervisor_evaluation_score = total_system_weighted_score
                
            final = (review.system_generated_score * Decimal('0.80')) + (review.supervisor_evaluation_score * Decimal('0.20'))
            review.final_score = final

            # Assign Rating Scale
            matching_rating = RatingScale.objects.filter(
                min_score__lte=final, max_score__gte=final
            ).first()
            review.rating = matching_rating
            review.save()

        return review