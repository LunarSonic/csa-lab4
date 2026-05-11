int limit = 4000000;
int a = 1;
int b = 2;
int sum = 0;
int temp = 0;
int next = 0;
while (b < limit) {
    temp = b % 2;
    if (temp == 0) {
        sum = sum + b;
    }
    next = a + b;
    a = b;
    b = next;
}
print(sum);
