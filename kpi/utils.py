import calendar
from datetime import date
from django.db import transaction

def ensure_monthly_cycle_and_summary(entry_date, floor=None, employee=None):
    """
    Checks if an EvaluationCycle exists for the month of `entry_date`.
    If missing, creates it immediately in SQL Server.
    Also ensures floor-level monthly summary rows are provisioned.
    """
    from kpi.models import EvaluationCycle
    from employees.models import MonthlyFloorProductionSummary, FloorProductionKPI
    from decimal import Decimal
    from django.db.models import Sum, Avg, Count

    year = entry_date.year
    month = entry_date.month

    m_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    m_end = date(year, month, last_day)

    # 1. Automatic EvaluationCycle creation in SQL Database
    cycle_name = f"{m_start.strftime('%B %Y')} • Monthly (1 Month) ({m_start.strftime('%d-%b-%Y')} to {m_end.strftime('%d-%b-%Y')})"
    
    cycle, _ = EvaluationCycle.objects.get_or_create(
        start_date=m_start,
        end_date=m_end,
        defaults={
            'name': cycle_name,
            'cycle_type': 'MONTHLY',
            'is_active': True,
        }
    )

    # 2. Automatic Monthly Summary Table Record sync (if floor is provided)
    if floor:
        daily_records = FloorProductionKPI.objects.filter(
            floor=floor,
            date__range=(m_start, m_end)
        )

        if daily_records.exists():
            agg = daily_records.aggregate(
                days=Count('id'),
                tot_target=Sum('target_quantity'),
                tot_produced=Sum('produced_quantity'),
                avg_eff=Avg('efficiency_rate'),
                avg_dhu=Avg('dhu_rate'),
                pass_qty=Sum('inspection_pass_qty'),
                fail_qty=Sum('inspection_fail_qty'),
                tot_ot=Sum('extra_ot_hours'),
                avg_ship=Avg('timely_shipment_rate'),
                avg_mgmt=Avg('floor_management_score'),
                tot_disc=Sum('disciplinary_count'),
                avg_kpi=Avg('kpi_rank_score')
            )

            latest_emp = daily_records.exclude(employee__isnull=True).order_by('-date').values_list('employee_id', flat=True).first()

            MonthlyFloorProductionSummary.objects.update_or_create(
                floor=floor,
                month=m_start,
                defaults={
                    'unit': floor.unit,
                    'employee_id': latest_emp,
                    'days_recorded': agg['days'] or 0,
                    'total_target': agg['tot_target'] or 0,
                    'total_produced': agg['tot_produced'] or 0,
                    'avg_efficiency': round(Decimal(str(agg['avg_eff'] or 0)), 2),
                    'avg_dhu': round(Decimal(str(agg['avg_dhu'] or 0)), 2),
                    'total_inspection_pass': agg['pass_qty'] or 0,
                    'total_inspection_fail': agg['fail_qty'] or 0,
                    'total_extra_ot': round(Decimal(str(agg['tot_ot'] or 0)), 2),
                    'avg_timely_shipment': round(Decimal(str(agg['avg_ship'] or 100)), 2),
                    'avg_floor_mgmt': round(Decimal(str(agg['avg_mgmt'] or 100)), 2),
                    'total_disciplinary': agg['tot_disc'] or 0,
                    'avg_kpi_score': round(Decimal(str(agg['avg_kpi'] or 0)), 2),
                }
            )

    return cycle