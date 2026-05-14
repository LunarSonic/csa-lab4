array arr = {100};
int n = 0;
read(n);

int count = 0;
while (count < n) {
    read(arr[count]);
    count = count + 1;
}

int i = 0;
int j = 0;
int temp = 0;

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

int k = 0;
while (k < n) {
    print(arr[k]);
    print("\n");
    k = k + 1;
}