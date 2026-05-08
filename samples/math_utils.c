/**
 * math_utils.c - Simple math utility functions for testing
 * Demonstrates normal, boundary, and error cases
 */

#include <math.h>

/**
 * add - Add two integers
 * @a: First operand
 * @b: Second operand
 * @return: Sum of a and b
 */
int add(int a, int b) {
    return a + b;
}

/**
 * subtract - Subtract two integers
 * @a: Minuend
 * @b: Subtrahend
 * @return: Difference (a - b)
 */
int subtract(int a, int b) {
    return a - b;
}

/**
 * multiply - Multiply two integers
 * @a: First factor
 * @b: Second factor
 * @return: Product of a and b
 */
int multiply(int a, int b) {
    return a * b;
}

/**
 * divide - Divide two integers
 * @a: Dividend
 * @b: Divisor (must not be zero)
 * @return: Quotient (a / b), or -1 on error
 */
int divide(int a, int b) {
    if (b == 0) {
        return -1;  /* Division by zero */
    }
    return a / b;
}

/**
 * absolute_value - Get absolute value of an integer
 * @x: Input value
 * @return: Absolute value of x
 */
int absolute_value(int x) {
    if (x < 0) {
        return -x;
    }
    return x;
}

/**
 * max - Return the maximum of two integers
 * @a: First value
 * @b: Second value
 * @return: Maximum of a and b
 */
int max(int a, int b) {
    return (a > b) ? a : b;
}

/**
 * min - Return the minimum of two integers
 * @a: First value
 * @b: Second value
 * @return: Minimum of a and b
 */
int min(int a, int b) {
    return (a < b) ? a : b;
}

/**
 * clamp - Clamp value to range [min_val, max_val]
 * @value: Value to clamp
 * @min_val: Minimum allowed value
 * @max_val: Maximum allowed value
 * @return: Clamped value
 */
int clamp(int value, int min_val, int max_val) {
    if (min_val > max_val) {
        return -1;  /* Error: invalid range */
    }
    if (value < min_val) return min_val;
    if (value > max_val) return max_val;
    return value;
}

/**
 * is_even - Check if number is even
 * @n: Number to check
 * @return: 1 if even, 0 if odd
 */
int is_even(int n) {
    return (n % 2 == 0) ? 1 : 0;
}

/**
 * power - Calculate x^n (power)
 * @base: Base value
 * @exponent: Exponent (must be non-negative)
 * @return: base^exponent, or -1 on error
 */
int power(int base, int exponent) {
    if (exponent < 0) {
        return -1;  /* Error: negative exponent */
    }
    int result = 1;
    for (int i = 0; i < exponent; i++) {
        result *= base;
    }
    return result;
}
