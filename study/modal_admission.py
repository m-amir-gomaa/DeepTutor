"""Conservative private-study admission, independent of public guest accounting."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import re

def admit(state, cycle, metered, billed, job_id, input_sha256, now, *, limit_usd=5, credit_ceiling_usd=30, reserve_usd=.25):
    try:
        metered=Decimal(str(metered));billed=Decimal(str(billed))
        limit=Decimal(str(limit_usd));ceiling=Decimal(str(credit_ceiling_usd));reserve=Decimal(str(reserve_usd))
    except InvalidOperation:raise ValueError('Invalid provider metering') from None
    if not all(n.is_finite() for n in [metered,billed,limit,ceiling,reserve]) or min(metered,billed)<0 or reserve<Decimal('.25') or limit<reserve or ceiling<=1:
        raise ValueError('Invalid provider metering')
    if billed>0 or metered+reserve>ceiling-1:
        raise ValueError('Workspace credit headroom is currently unavailable. Use local processing.')
    if not re.fullmatch(r'\d{4}-\d{2}',cycle):raise ValueError('Invalid provider cycle')
    data=deepcopy(state) if state and state['cycle']==cycle else {'cycle':cycle,'jobs':{}}
    if job_id in data['jobs']:raise ValueError('This job was already admitted; inspect its local receipt before retrying.')
    used=sum(Decimal(str(r['reserved_usd'])) for r in data['jobs'].values())
    if used+reserve>limit:raise ValueError('The monthly personal-study reservation cap is reached. Use local processing.')
    data['jobs'][job_id]={'reserved_usd':float(reserve),'at':now,'input_sha256':input_sha256}
    return data
