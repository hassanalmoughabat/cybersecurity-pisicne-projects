#include <string.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	if (argc != 2)
	{
		char	password[100];

		printf("Please enter key: \n");
		scanf("%s", password);
		if (strcmp(password, "00101108097098101114101") == 0)
			printf("Good job.");
		else
		printf("Nope");
	}
	printf("\n");
}
