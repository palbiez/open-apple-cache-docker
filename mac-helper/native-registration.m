#import <Foundation/Foundation.h>
#import <objc/message.h>
#import <objc/runtime.h>
#import <dlfcn.h>
#import <fcntl.h>
#import <ptrauth.h>
#import <unistd.h>

static void *BranchTarget(void *implementation, size_t offset) {
    uintptr_t instructionAddress = (uintptr_t)implementation + offset;
    uint32_t instruction = *(uint32_t *)instructionAddress;
    if ((instruction & 0xfc000000) != 0x94000000) return NULL;
    int64_t immediate = instruction & 0x03ffffff;
    if (immediate & 0x02000000) immediate -= 0x04000000;
    return (void *)(instructionAddress + (immediate << 2));
}

static int WriteNewFile(const char *path, NSData *data) {
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0) return 1;
    const uint8_t *bytes = data.bytes;
    NSUInteger remaining = data.length;
    while (remaining) {
        ssize_t count = write(fd, bytes, remaining);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) { close(fd); return 1; }
        bytes += count;
        remaining -= (NSUInteger)count;
    }
    int syncResult = fsync(fd);
    int closeResult = close(fd);
    return syncResult || closeResult;
}

int main(int argc, const char *argv[]) { @autoreleasepool {
    if (argc != 5) {
        fprintf(stderr, "usage: native-registration CERTIFICATE SESSION_URL PAYLOAD OUTPUT_NEW_FILE\n");
        return 64;
    }
    if (!dlopen("/System/Library/PrivateFrameworks/AuthKit.framework/AuthKit", RTLD_LAZY)) return 1;
    Class cls = NSClassFromString(@"AKAbsintheSigner");
    id signer = [[cls alloc] init];
    NSData *certificate = [NSData dataWithContentsOfFile:@(argv[1])];
    NSURL *sessionURL = [NSURL URLWithString:@(argv[2])];
    SEL sessionSelector = NSSelectorFromString(@"_sessionInfoFromCertificateData:");
    NSData *sessionInfo = ((id (*)(id, SEL, id))objc_msgSend)(signer, sessionSelector, certificate);
    if (!sessionInfo.length) return 2;

    dispatch_semaphore_t establishedSemaphore = dispatch_semaphore_create(0);
    __block BOOL established = NO;
    SEL establishSelector = NSSelectorFromString(
        @"_establishSessionWithInfo:sessionURL:completionHandler:");
    void (^establishedCallback)(BOOL, NSError *) = ^(BOOL success, NSError *error) {
        established = success && error == nil;
        dispatch_semaphore_signal(establishedSemaphore);
    };
    ((void (*)(id, SEL, id, id, id))objc_msgSend)(
        signer, establishSelector, sessionInfo, sessionURL, establishedCallback);
    if (dispatch_semaphore_wait(establishedSemaphore,
            dispatch_time(DISPATCH_TIME_NOW, 25 * NSEC_PER_SEC)) || !established) return 3;

    NSData *templateData = [NSData dataWithContentsOfFile:@(argv[3])];
    NSError *jsonError = nil;
    NSMutableDictionary *registration = [[NSJSONSerialization
        JSONObjectWithData:templateData options:NSJSONReadingMutableContainers error:&jsonError]
        mutableCopy];
    NSString *sessionToken = nil;
    for (NSHTTPCookie *cookie in [[NSHTTPCookieStorage sharedHTTPCookieStorage]
            cookiesForURL:sessionURL]) {
        if ([cookie.name isEqualToString:@"LCDN-Session"]) sessionToken = cookie.value;
    }
    if (jsonError || !registration || !sessionToken.length) return 4;
    registration[@"session-token"] = sessionToken;
    NSData *payload = [NSJSONSerialization dataWithJSONObject:registration options:0 error:&jsonError];
    if (jsonError || !payload.length) return 4;

    SEL signatureSelector = NSSelectorFromString(@"_generateSignatureForRequest:completionHandler:");
    Method method = class_getInstanceMethod(cls, signatureSelector);
    void *implementation = ptrauth_strip(method_getImplementation(method),
                                          ptrauth_key_function_pointer);
    void *rawFunction = BranchTarget(implementation, 0x248);
    Ivar contextIvar = class_getInstanceVariable(cls, "_context");
    void *context = *(void **)((uint8_t *)(__bridge void *)signer + ivar_getOffset(contextIvar));
    if (!rawFunction || !context) return 5;
    typedef int (*NACSignFunction)(void *, const void *, size_t, void **, uint32_t *);
    NACSignFunction nacSign = ptrauth_sign_unauthenticated(
        rawFunction, ptrauth_key_function_pointer, 0);
    void *signedBytes = NULL;
    uint32_t signedLength = 0;
    int status = nacSign(context, payload.bytes, payload.length, &signedBytes, &signedLength);
    if (status != 0 || !signedBytes || signedLength <= payload.length) return 6;
    NSData *signedData = [NSData dataWithBytes:signedBytes length:signedLength];
    if (WriteNewFile(argv[4], signedData)) return 7;
    fprintf(stderr, "signed_registration_bytes=%u\n", signedLength);
} return 0; }
