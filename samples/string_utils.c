/**
 * string_utils.c - String manipulation utility functions
 * Demonstrates pointer handling and boundary cases
 */

#include <string.h>
#include <ctype.h>

/**
 * string_length - Get length of null-terminated string
 * @str: Pointer to string (must not be NULL)
 * @return: Length of string, or -1 if NULL
 */
int string_length(const char* str) {
    if (str == NULL) {
        return -1;
    }
    int len = 0;
    while (str[len] != '\0') {
        len++;
    }
    return len;
}

/**
 * string_compare - Compare two strings
 * @s1: First string
 * @s2: Second string
 * @return: 0 if equal, <0 if s1<s2, >0 if s1>s2, or -2 if either is NULL
 */
int string_compare(const char* s1, const char* s2) {
    if (s1 == NULL || s2 == NULL) {
        return -2;
    }
    return strcmp(s1, s2);
}

/**
 * string_concat - Concatenate two strings
 * @dest: Destination buffer (must be large enough)
 * @src: Source string (must not be NULL)
 * @return: Pointer to dest, or NULL on error
 */
char* string_concat(char* dest, const char* src) {
    if (dest == NULL || src == NULL) {
        return NULL;
    }
    while (*dest != '\0') {
        dest++;
    }
    while ((*dest = *src) != '\0') {
        dest++;
        src++;
    }
    return dest;
}

/**
 * char_is_digit - Check if character is a digit
 * @c: Character to check
 * @return: 1 if digit, 0 otherwise
 */
int char_is_digit(char c) {
    return (c >= '0' && c <= '9') ? 1 : 0;
}

/**
 * char_is_alpha - Check if character is alphabetic
 * @c: Character to check
 * @return: 1 if alpha, 0 otherwise
 */
int char_is_alpha(char c) {
    return ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) ? 1 : 0;
}

/**
 * char_to_upper - Convert character to uppercase
 * @c: Character to convert
 * @return: Uppercase version of c, or unchanged if not a letter
 */
char char_to_upper(char c) {
    if (c >= 'a' && c <= 'z') {
        return c - 32;
    }
    return c;
}

/**
 * char_to_lower - Convert character to lowercase
 * @c: Character to convert
 * @return: Lowercase version of c, or unchanged if not a letter
 */
char char_to_lower(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c + 32;
    }
    return c;
}

/**
 * string_index_of - Find first occurrence of character in string
 * @str: String to search (must not be NULL)
 * @ch: Character to find
 * @return: Index of first occurrence, or -1 if not found or str is NULL
 */
int string_index_of(const char* str, char ch) {
    if (str == NULL) {
        return -1;
    }
    for (int i = 0; str[i] != '\0'; i++) {
        if (str[i] == ch) {
            return i;
        }
    }
    return -1;
}

/**
 * string_last_index_of - Find last occurrence of character in string
 * @str: String to search (must not be NULL)
 * @ch: Character to find
 * @return: Index of last occurrence, or -1 if not found or str is NULL
 */
int string_last_index_of(const char* str, char ch) {
    if (str == NULL) {
        return -1;
    }
    int last_idx = -1;
    for (int i = 0; str[i] != '\0'; i++) {
        if (str[i] == ch) {
            last_idx = i;
        }
    }
    return last_idx;
}
