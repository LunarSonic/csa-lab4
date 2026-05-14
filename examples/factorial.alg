int n = 0;
int res = 1;
read(n);
while (n > 1) {
    res = res * n;
    n = n - 1;
}
print(res);