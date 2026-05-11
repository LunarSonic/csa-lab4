array arr = {5};
arr[0] = 42;
arr[1] = 7;
arr[2] = 15;
arr[3] = 3;
arr[4] = 20;

int n = 5;
int i = 0;
int j = 0;
int temp = 0;
int k = 0;

while (i < n) {
    j = 0;
    while (j < ((n - i) - 1)) {
        if (arr[j] > arr[j + 1]) {
            temp = arr[j];
            arr[j] = arr[j + 1];
            arr[j + 1] = temp;
        }
        j = j + 1;
    }
    i = i + 1;
}
while (k < n) {
    print(arr[k]);
    print("\n");
    k = k + 1;
}
