long a = 5000000000;
long b = 3000000000;
long c = 7000000000;
long d = 4294967295;
long e = 1000000000;
long f = 8500000000;

int m = 2147483647;
int zero = 0;

long res1 = ((a + c) - f) + e;
long res2 = (a & d) | (c & d);
long res3 = (a - 1) & m;
long res4 = (!a < (b + c)) > e;
long res5 = (((((((a + b) + c) + d) + e) + f) - a) + c) + f;
long res6 = a || (b & (c + 0));

print(res1[1]);
print(" ");
print(res2[1]);
print(" ");
print(res3[1]);
print(" ");
print(res4[1]);
print(" ");
print(res5[1]);
print(" ");
print(res1[0]);