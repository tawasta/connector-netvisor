# Import "netvisor"-models first to ensure shared bindings etc. exist
from . import netvisor_backend
from . import netvisor_binding

# Import rest of the models in alphabetical order
from . import account_analytic_account
from . import account_analytic_plan
from . import account_move
from . import account_payment
from . import account_tax
from . import partner
from . import product
