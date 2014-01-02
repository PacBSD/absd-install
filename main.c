#include <stdio.h>
#include <string.h>
#include <libgeom.h>

typedef struct gctl_req req_t;

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "doit")) {
        printf("No\n");
        exit(1);
        return 1;
    }
    req_t *h = gctl_get_handle();
    gctl_ro_param(h, "class", -1, "PART");
    gctl_ro_param(h, "verb", -1, "delete");
    gctl_ro_param(h, "geom", -1, "ada1");
    gctl_ro_param(h, "index", -1, "1");
    const char *errstr = gctl_issue(h);
    if (errstr) {
        printf(": %s\n", errstr);
        gctl_dump(h, stdout);
    }
    else
        printf("ERROR\n");
    gctl_free(h);
    return 0;
}
