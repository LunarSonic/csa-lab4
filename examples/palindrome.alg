array s = {40};
int len = 0;
int i = 0;
int is_palindrome = 1;
print("Enter word:\n");
read(s);
while (s[len] != 0) {
    len = len + 1;
}
while (i < (len / 2)) {
    if (s[i] != s[(len - 1) - i]) {
        is_palindrome = 0;
    }
    i = i + 1;
}
if (is_palindrome == 1) {
    print("Yes, it's a palindrome");
} else {
    print("No, it's not a palindrome");
}
