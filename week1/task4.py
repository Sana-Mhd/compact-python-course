n = int(input("Enter a number: "))

result = 1
for i in range(1, n + 1):
    result *= i

print("Factorial of", n, "is", result)
