long account_balance = 8000000000;
long transaction_amount = 3000000000;
long reserve = 1000000000;
int is_blocked = 0;
int force_approve = 0;
if ((((account_balance - transaction_amount) > reserve) && !is_blocked) || (force_approve == 1)) {
    print("Transaction is approved");
} else {
    print("Transaction is denied");
}
